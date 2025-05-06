import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from time import perf_counter, sleep
from time import time as now
from typing import Any, Dict, List

import ecal.core.core as ecal_core
import yaml
# NOTE: see relevant note about ProtoPublisher in eCALPublisher below
# from ecal.core.publisher import ProtoPublisher
from lcm import LCM

from bench_pb2 import Bench
from benchmark import (LCMHandshake, compute_stats, eCALMonitor,
                       generate_lcm_benchmark_msg,
                       generate_proto_benchmark_msg)
from lcmtypes import bench_t

logger = logging.getLogger(__name__)


class BenchmarkMessage:
    def __init__(self, num_bytes: int, middleware: str):
        if middleware == "lcm":
            self._inner: bench_t | Bench = generate_lcm_benchmark_msg(num_bytes)
        else:
            self._inner: bench_t | Bench = generate_proto_benchmark_msg(num_bytes)
        self.num_bytes = num_bytes
        self.middleware = middleware
        self.creation_time_ns = self._inner.creation_timestamp_ns

    def serialize(self) -> bytes:
        if type(self._inner) == bench_t:
            return self._inner.encode()
        elif type(self._inner) == Bench:
            return self._inner.SerializeToString()
        raise ValueError("self._inner must be either a bench_t or Bench message")


class BasePublisher:
    def send(self, data: bytes) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass

    def msg_type(self) -> type:
        raise NotImplementedError


class LcmPublisher(BasePublisher):
    def __init__(self, url: str, channel: str):
        self._conn = LCM(provider=url)
        self._channel = channel

        handshake = LCMHandshake(url, channel)
        handshake.wait_for_subscriber()

    def send(self, data: bytes) -> None:
        self._conn.publish(self._channel, data)

    def msg_type(self) -> type:
        return bench_t


class eCALPublisher(BasePublisher):
    def __init__(self, topic: str):
        ecal_core.initialize(sys.argv, f"benchmark_publisher_{topic}")
        # NOTE: We purposefully do not use ProtoPublisher so that we can
        #       measure the decode time directly by doing it ourselves
        # self._pub = ProtoPublisher(topic, Bench)
        self._pub = ecal_core.publisher(topic, "proto:" + Bench.DESCRIPTOR.full_name)
        logger.info(
            f"Waiting for at least one subscriber to register to topic {topic}..."
        )

        with eCALMonitor() as monitor:
            while not monitor.has_subscriber(topic):
                sleep(0.01)
        logger.info(
            f"Found at least one subscriber for {topic}. Continuing on to rest of process path"
        )

    def send(self, data: bytes) -> None:
        self._pub.send(data)

    def msg_type(self) -> type:
        return Bench

    def close(self) -> None:
        ecal_core.finalize()


def main(
    middleware: str,
    lcm_url: str,
    channel_name: str,
    transmission_rate_setpoint: int,
    num_bytes: int,
    num_msgs: int,
    results_dir: Path | str,
    log_level: str,
    log_output: str,
) -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=getattr(logging, log_level),
        filename=log_output,
    )
    logger.info(
        f"Starting benchmark ({middleware}): "
        f"channel={channel_name!r}, rate={transmission_rate_setpoint}Hz, "
        f"num_bytes={num_bytes}, num_msgs={num_msgs}"
    )

    assert middleware in ("lcm", "ecal"), "middleware must be 'lcm' or 'ecal'"
    assert transmission_rate_setpoint > 0, "transmission_rate_setpoint must be > 0"
    assert num_msgs > 0, "num_msgs must be > 0"

    if isinstance(results_dir, str):
        results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    if middleware == "lcm":
        publisher: BasePublisher = LcmPublisher(lcm_url, channel_name)
    elif middleware == "ecal":
        publisher = eCALPublisher(channel_name)
    else:
        raise ValueError(f"{middleware} not supported")

    period_s = 1.0 / transmission_rate_setpoint
    serialization_durations_ms: List[float] = []
    publish_durations_ms: List[float] = []
    overshot_durations_ms: List[float] = []
    publish_timestamps_s: List[float] = []

    for i in range(num_msgs):
        loop_start = perf_counter()

        bm = BenchmarkMessage(num_bytes, middleware)

        t0 = perf_counter()
        data = bm.serialize()
        t1 = perf_counter()
        serialize_ms = (t1 - t0) * 1e3

        t2 = perf_counter()
        publisher.send(data)
        t3 = perf_counter()
        publish_ms = (t3 - t2) * 1e3

        total_s = t3 - loop_start

        logger.info(
            f"{'(ignoring first message in saved report)' if i == 0 else ''} "
            f"Sent msg {i+1}/{num_msgs}: ({num_bytes} bytes) (creation_time_ns={bm.creation_time_ns}) "
            f"encode msg took {serialize_ms:.3f} ms, send msg took {publish_ms:.3f} ms "
        )

        if i == 0:
            # NOTE: we do not "count" first message durations in reported statistics as it includes
            #       extra overhead that the other messages don't have
            if total_s < period_s:
                sleep(period_s - total_s)
            continue

        serialization_durations_ms.append(serialize_ms)
        publish_durations_ms.append(publish_ms)
        publish_timestamps_s.append(t3)

        if total_s < period_s:
            sleep(period_s - total_s)
        else:
            over_ms = (total_s - period_s) * 1e3
            overshot_durations_ms.append(over_ms)
            logger.debug(
                f"Publish loop overshot by {over_ms:.3f} ms (period was {period_s*1e3:.3f} ms)"
            )

    publisher.close()

    serialize_stats = compute_stats(serialization_durations_ms, "ms")
    publish_stats = compute_stats(publish_durations_ms, "ms")
    overshot_stats = (
        compute_stats(overshot_durations_ms, "ms") if overshot_durations_ms else {}
    )
    actual_rates_hz = [
        1.0 / (t2 - t1)
        for t1, t2 in zip(publish_timestamps_s, publish_timestamps_s[1:])
        if t2 > t1
    ]
    rate_stats = compute_stats(actual_rates_hz, "hz") if actual_rates_hz else {}

    report: Dict[str, Any] = {
        "timestamp_us": int(now() * 1e6),
        "parameters": {
            "middleware": middleware,
            "channel_name": channel_name,
            "transmission_rate_hz_setpoint": transmission_rate_setpoint,
            "num_bytes": num_bytes,
            "num_msgs": num_msgs,
            "message_type": str(publisher.msg_type()),
        },
        "serialization_durations_ms": serialization_durations_ms,
        "serialization_duration_statistics": serialize_stats,
        "publish_durations_ms": publish_durations_ms,
        "publish_duration_statistics": publish_stats,
        "overshot_publish_durations_ms": overshot_durations_ms,
        "overshot_publish_duration_statistics": overshot_stats,
        "actual_transmission_rates_hz": actual_rates_hz,
        "actual_transmission_rate_statistics": rate_stats,
    }

    out = (
        results_dir / f"{middleware}_publisher_benchmark_{report['timestamp_us']}.yaml"
    )
    with open(out, "w") as f:
        yaml.dump(report, f)
    logger.info(f"Wrote report to {out}")


if __name__ == "__main__":
    parser = ArgumentParser(description="Benchmark LCM or eCAL publisher")
    parser.add_argument("--middleware", choices=("lcm", "ecal"), default="lcm")
    parser.add_argument(
        "--lcm-url", type=str, default="udpm://239.255.76.67:7667?ttl=1"
    )
    parser.add_argument("--channel-name", type=str, default="/benchmark")
    parser.add_argument("--transmission-rate", type=int, default=100)
    parser.add_argument("--num-bytes", type=int, default=1024)
    parser.add_argument("--num-msgs", type=int, default=5)
    parser.add_argument("--results-dir", type=str, default="./results")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level. (default=INFO)",
    )
    parser.add_argument(
        "--log-output",
        type=str,
        default="",
        help='Optional path to a log file. If value is None or "" then will log to stdout/stderr (default=None)',
    )

    parser.add_argument(
        "--ecal-ini-file",
        type=Path,
        default=Path("/etc/ecal/ecal.ini"),
        help="Optional path to the ecal.ini file to use for this process",
    )
    args = parser.parse_args()

    main(
        middleware=args.middleware,
        lcm_url=args.lcm_url,
        channel_name=args.channel_name,
        transmission_rate_setpoint=args.transmission_rate,
        num_bytes=args.num_bytes,
        num_msgs=args.num_msgs,
        results_dir=args.results_dir,
        log_level=args.log_level,
        log_output=args.log_output,
    )
