import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from queue import Empty, Queue
from time import perf_counter, sleep
from time import time as now
from time import time_ns
from typing import Any, Dict, List

import ecal.core.core as ecal_core
import yaml
from lcm import LCM

from bench_pb2 import Bench
from benchmark import LCMHandshake, compute_stats
from lcmtypes import bench_t, status_t
from status_pb2 import Status

logger = logging.getLogger(__name__)


class BenchmarkMessage:
    def __init__(
        self,
        num_bytes: int,
        blob: bytes,
        creation_time_ns: int,
        msg_type: Any,
        total_msgs: int,
        idx: int,
    ):
        self.num_bytes = num_bytes
        self.blob = blob
        self.creation_time_ns = creation_time_ns
        self.msg_type = msg_type
        self.total_msgs = total_msgs
        self.idx = idx

    @classmethod
    def from_lcm(cls, raw: bench_t) -> "BenchmarkMessage":
        return cls(
            raw.num_bytes,
            bytes(raw.blob),
            raw.creation_timestamp_ns,
            bench_t,
            raw.total_number_of_messages,
            raw.message_number,
        )

    @classmethod
    def from_proto(cls, msg: Bench) -> "BenchmarkMessage":
        return cls(
            len(msg.blob),
            msg.blob,
            msg.creation_timestamp_ns,
            Bench,
            msg.total_number_of_messages,
            msg.message_number,
        )


class LcmSubscriber:
    def __init__(self, url: str, channel: str):
        self._conn = LCM(provider=url)
        self._last = None
        self._conn.subscribe(channel, self._cb)
        # handshake back to publisher
        hs = LCMHandshake(url, channel)
        hs.send_ready()

    def _cb(self, topic, data):
        self._last = data

    def receive(self, timeout_s: float = None):
        t0 = perf_counter()
        if timeout_s is None:
            self._conn.handle()
        else:
            self._conn.handle_timeout(int(timeout_s * 1e3))
            if self._last is None:
                raise TimeoutError()
        handle_ms = (perf_counter() - t0) * 1e3

        raw = bench_t.decode(self._last)
        self._last = None

        t1 = perf_counter()
        bm = BenchmarkMessage.from_lcm(raw)
        decode_ms = (perf_counter() - t1) * 1e3

        return bm, handle_ms, decode_ms


class EcalSubscriber:
    def __init__(self, channel: str):
        ecal_core.initialize(sys.argv, f"benchmark_subscriber_{channel}")
        self._sub = ecal_core.subscriber(channel, "proto:" + Bench.DESCRIPTOR.full_name)
        self._queue = Queue()
        self._sub.set_callback(self._cb)

    def _cb(self, topic, raw, ts):
        self._queue.put(raw)

    def receive(self, timeout_s: float = None):
        t0 = perf_counter()
        try:
            if timeout_s is None:
                raw = self._queue.get()
            else:
                raw = self._queue.get(timeout=timeout_s)
        except Empty:
            raise TimeoutError()
        handle_ms = (perf_counter() - t0) * 1e3

        t1 = perf_counter()
        msg = Bench()
        msg.ParseFromString(raw)
        bm = BenchmarkMessage.from_proto(msg)
        decode_ms = (perf_counter() - t1) * 1e3

        return bm, handle_ms, decode_ms

    def close(self):
        ecal_core.finalize()


def make_status_pub(middleware: str, lcm_url: str, channel: str):
    status_chan = f"{channel}_status"
    if middleware == "lcm":
        lc = LCM(provider=lcm_url)
        return lambda msg: lc.publish(status_chan, msg.encode())
    else:
        pub = ecal_core.publisher(status_chan, "proto:" + Status.DESCRIPTOR.full_name)
        return lambda msg: pub.send(msg.SerializeToString())


def main(
    middleware: str,
    lcm_url: str,
    channel_name: str,
    timeout_s: float,
    results_dir: str,
    log_level: str,
    log_output: str,
):
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=getattr(logging, log_level),
        filename=(log_output or None),
    )
    logger.info(f"Starting subscriber ({middleware}) on {channel_name!r}")

    results_dir = Path(results_dir) / str(time_ns())
    results_dir.mkdir(parents=True, exist_ok=True)

    # choose subscriber
    if middleware == "lcm":
        sub = LcmSubscriber(lcm_url, channel_name)
    else:
        sub = EcalSubscriber(channel_name)

    # first message: determine total msgs
    try:
        bm0, h0, d0 = sub.receive(timeout_s)
    except TimeoutError:
        logger.error("Timed out waiting for first message → cannot proceed")
        sys.exit(1)

    total = bm0.total_msgs
    logger.info(f"Expecting {total} messages (got first idx={bm0.idx})")

    # collect stats
    handles = []
    decodes = []
    oneways = []
    sizes = []

    # first one is warmup; skip for stats
    prev_ts = bm0.creation_time_ns / 1e9

    # process the rest
    success = True
    for count in range(1, total):
        try:
            bm, h, d = sub.receive(timeout_s)
        except TimeoutError:
            logger.error(f"Timed out at msg {count}/{total}")
            success = False
            break

        now_ns = time_ns()
        oneway = (now_ns - bm.creation_time_ns) / 1e6

        handles.append(h)
        decodes.append(d)
        oneways.append(oneway)
        sizes.append(bm.num_bytes)

        prev_ts = bm.creation_time_ns / 1e9

    # send back status
    status_pub = make_status_pub(middleware, lcm_url, channel_name)
    msg = status_t()
    msg.pid = os.getpid()
    msg.success = success
    msg.retry_number = bm0.idx  # echo first message number
    status_pub(msg)

    sub.close() if middleware == "ecal" else None

    # write record
    stats = {
        "timestamp_us": int(now() * 1e6),
        "channel": channel_name,
        "success": success,
        "parameters": {
            "total_msgs": total,
            "timeout_s": timeout_s,
        },
        "handle_statistics": compute_stats(handles, "ms") if handles else {},
        "decode_statistics": compute_stats(decodes, "ms") if decodes else {},
        "oneway_statistics": compute_stats(oneways, "ms") if oneways else {},
        "size_statistics": compute_stats(sizes, "bytes") if sizes else {},
    }

    out = results_dir / f"{middleware}_subscriber_report_{stats['timestamp_us']}.yaml"
    with open(out, "w") as f:
        yaml.dump(stats, f)
    logger.info(f"Wrote report to {out}")


if __name__ == "__main__":
    p = ArgumentParser(description="Benchmark LCM/eCAL subscriber w/timeout")
    p.add_argument("--middleware", choices=("lcm", "ecal"), default="lcm")
    p.add_argument("--lcm-url", default="udpm://239.255.76.67:7667?ttl=1")
    p.add_argument("--channel-name", default="/benchmark")
    p.add_argument("--timeout-s", type=float, default=3.0)
    p.add_argument("--results-dir", default="./results")
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
        timeout_s=args.timeout_s,
        results_dir=args.results_dir,
        log_level=args.log_level,
        log_output=args.log_output,
    )
