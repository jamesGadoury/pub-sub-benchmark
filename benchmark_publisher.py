import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from time import perf_counter, sleep
from time import time as now
from time import time_ns
from typing import Any, Dict, List

import ecal.core.core as ecal_core
import yaml
from lcm import LCM

from bench_pb2 import Bench
from benchmark import (LCMHandshake, compute_stats, generate_lcm_benchmark_msg,
                       generate_proto_benchmark_msg)
from lcmtypes import bench_t, status_t
from status_pb2 import Status

logger = logging.getLogger(__name__)


class BenchmarkMessage:
    def __init__(self, num_bytes: int, middleware: str):
        self.middleware = middleware
        if middleware == "lcm":
            self._inner: bench_t = generate_lcm_benchmark_msg(num_bytes)
        else:
            self._inner: Bench = generate_proto_benchmark_msg(num_bytes)

        self.num_bytes = num_bytes
        self.creation_time_ns = (
            self._inner.creation_timestamp_ns
            if middleware == "lcm"
            else self._inner.creation_timestamp_ns
        )

    def serialize(self, total_msgs: int, idx: int) -> bytes:
        if self.middleware == "lcm":
            inner: bench_t = self._inner
            inner.total_number_of_messages = total_msgs
            inner.message_number = idx
            return inner.encode()
        else:
            proto: Bench = self._inner
            proto.total_number_of_messages = total_msgs
            proto.message_number = idx
            return proto.SerializeToString()


def make_publisher(middleware: str, lcm_url: str, channel: str):
    if middleware == "lcm":
        pub = LCM(provider=lcm_url)
        # wait-for-subscriber handshake
        handshake = LCMHandshake(lcm_url, channel)
        handshake.wait_for_subscriber()
        return pub.publish
    else:
        ecal_core.initialize(sys.argv, f"benchmark_publisher_{channel}")
        publisher = ecal_core.publisher(channel, "proto:" + Bench.DESCRIPTOR.full_name)
        # wait for subscriber
        from benchmark import eCALMonitor

        with eCALMonitor():
            pass
        return publisher.send


def make_status_listener(middleware: str, lcm_url: str, channel: str, state, on_status):
    status_chan = f"{channel}_status"
    if middleware == "lcm":
        lc = LCM(provider=lcm_url)
        lc.subscribe(status_chan, on_status)
        return lc.handle_timeout
    else:
        # eCAL subscriber
        ecal_core.initialize(sys.argv, f"status_listener_{channel}")
        sub = ecal_core.subscriber(status_chan, "proto:" + Status.DESCRIPTOR.full_name)
        queue = []

        def cb(topic, raw, ts):
            st = Status()
            st.ParseFromString(raw)
            queue.append(st)

        sub.set_callback(cb)

        def poll(timeout_ms: int):
            # spin-wait for up to timeout_ms
            import time

            deadline = time.time() + timeout_ms / 1000.0
            while time.time() < deadline:
                if queue:
                    st = queue.pop(0)
                    on_status(status_chan, st)
                    return
            # timeout with no callback
            return

        return poll


def make_status_publisher(middleware: str, lcm_url: str, channel: str):
    status_chan = f"{channel}_status"
    if middleware == "lcm":
        lc = LCM(provider=lcm_url)
        return lambda msg: lc.publish(status_chan, msg.encode())
    else:
        # eCAL publisher for Status
        pub = ecal_core.publisher(status_chan, "proto:" + Status.DESCRIPTOR.full_name)
        return lambda msg: pub.send(msg.SerializeToString())


def main(
    middleware: str,
    lcm_url: str,
    channel_name: str,
    transmission_rate: int,
    num_bytes: int,
    num_msgs: int,
    results_dir: str,
    max_retries: int,
    timeout_s: float,
    log_level: str,
    log_output: str,
):
    # setup logging
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=getattr(logging, log_level),
        filename=(log_output or None),
    )
    logger.info(
        f"Starting benchmark ({middleware}): channel={channel_name!r}, "
        f"rate={transmission_rate}Hz, size={num_bytes}B, msgs={num_msgs}"
    )

    results_dir = Path(results_dir) / str(time_ns())
    results_dir.mkdir(parents=True, exist_ok=True)

    send = make_publisher(middleware, lcm_url, channel_name)
    status_pub = make_status_publisher(middleware, lcm_url, channel_name)

    # state for listener
    state = {"got": False, "success": False, "retry": -1}

    def on_status(topic, payload):
        # payload is decoded Status object for eCAL, raw bytes for LCM
        if middleware == "lcm":
            st = status_t.decode(payload)
        else:
            st = payload  # already parsed in callback
        if st.pid != os.getpid():
            return
        if st.retry_number != state["retry"]:
            return
        state["got"] = True
        state["success"] = st.success

    poll_status = make_status_listener(
        middleware, lcm_url, channel_name, state, on_status
    )

    all_attempts = []
    period_s = 1.0 / transmission_rate

    for attempt in range(max_retries):
        state.update(got=False, success=False, retry=attempt)
        serialization_ms = []
        publish_ms = []
        timestamps = []

        logger.info(
            f"Attempt {attempt}: sending {num_msgs} messages at {1/period_s:.1f}Hz"
        )
        for i in range(num_msgs):
            bm = BenchmarkMessage(num_bytes, middleware)

            t0 = perf_counter()
            data = bm.serialize(num_msgs, i)
            t1 = perf_counter()
            serialization_ms.append((t1 - t0) * 1e3)

            t2 = perf_counter()
            send(data)
            t3 = perf_counter()
            publish_ms.append((t3 - t2) * 1e3)

            timestamps.append(t3)

            # enforce rate
            elapsed = t3 - t0
            if elapsed < period_s:
                sleep(period_s - elapsed)

        # wait for subscriber status
        deadline = perf_counter() + timeout_s
        while perf_counter() < deadline and not state["got"]:
            poll_status(int(10))  # 10ms slices

        success = state["got"] and state["success"]
        if success:
            logger.info(f"Attempt {attempt} succeeded")
        else:
            logger.warning(f"Attempt {attempt} failed—will retry at half rate")
            transmission_rate = max(1, transmission_rate // 2)
            period_s = 1.0 / transmission_rate

        # record stats
        serialize_stats = compute_stats(serialization_ms[1:], "ms")
        publish_stats = compute_stats(publish_ms[1:], "ms")
        rate_stats = (
            compute_stats(
                [1.0 / (t2 - t1) for t1, t2 in zip(timestamps, timestamps[1:])], "hz"
            )
            if len(timestamps) > 1
            else {}
        )

        all_attempts.append(
            {
                "attempt": attempt,
                "rate_hz": transmission_rate,
                "success": success,
                "serialization_statistics": serialize_stats,
                "publish_statistics": publish_stats,
                "rate_statistics": rate_stats,
            }
        )

        if success:
            break

    if not all_attempts[-1]["success"]:
        # tell subscriber to stop
        msg = status_t()
        msg.pid = os.getpid()
        msg.success = False
        msg.retry_number = -1
        status_pub(msg)
        logger.error("Exhausted retries—exiting with failure")
        sys.exit(1)

    # write full report
    report = {
        "timestamp_us": int(now() * 1e6),
        "channel": channel_name,
        "attempts": all_attempts,
    }
    out = results_dir / f"{middleware}_publisher_report_{report['timestamp_us']}.yaml"
    with open(out, "w") as f:
        yaml.dump(report, f)
    logger.info(f"Wrote report to {out}")


if __name__ == "__main__":
    p = ArgumentParser(description="Benchmark LCM/eCAL publisher with retries")
    p.add_argument("--middleware", choices=("lcm", "ecal"), default="lcm")
    p.add_argument("--lcm-url", default="udpm://239.255.76.67:7667?ttl=1")
    p.add_argument("--channel-name", default="/benchmark")
    p.add_argument("--transmission-rate", type=int, default=100)
    p.add_argument("--num-bytes", type=int, default=1024)
    p.add_argument("--num-msgs", type=int, default=5)
    p.add_argument("--results-dir", default="./results")
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--timeout-s", type=float, default=3.0)
    p.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO"
    )
    p.add_argument("--log-output", default="")
    p.add_argument(
        "--ecal-ini-file",
        type=Path,
        default=Path("/etc/ecal/ecal.ini"),
        help="Optional path to the ecal.ini file to use for this process",
    )
    args = p.parse_args()

    main(
        middleware=args.middleware,
        lcm_url=args.lcm_url,
        channel_name=args.channel_name,
        transmission_rate=args.transmission_rate,
        num_bytes=args.num_bytes,
        num_msgs=args.num_msgs,
        results_dir=args.results_dir,
        max_retries=args.max_retries,
        timeout_s=args.timeout_s,
        log_level=args.log_level,
        log_output=args.log_output,
    )
