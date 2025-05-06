import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from queue import Full as QueueFull
from queue import Queue
from time import perf_counter
from time import time as now
from time import time_ns
from typing import Any, Dict, List, Tuple

import ecal.core.core as ecal_core
import yaml
# NOTE: see relevant note about ProtoSubscriber in eCALSubscriber below
# from ecal.core.subscriber import ProtoSubscriber
from lcm import LCM

from bench_pb2 import Bench
from benchmark import LCMHandshake, compute_stats
from lcmtypes import bench_t

logger = logging.getLogger(__name__)


class BenchmarkMessage:
    """
    Uniform wrapper for both LCM bench_t and Protobuf Bench messages.
    """

    def __init__(
        self, num_bytes: int, blob: bytes, creation_time_ns: int, msg_type: type
    ):
        self.num_bytes = num_bytes
        self.blob = blob
        self.creation_time_ns = creation_time_ns
        self.msg_type: type = msg_type

    @classmethod
    def from_lcm(cls, lcm_msg: bench_t) -> "BenchmarkMessage":
        return cls(
            lcm_msg.num_bytes,
            bytes(lcm_msg.blob),
            lcm_msg.creation_timestamp_ns,
            bench_t,
        )

    @classmethod
    def from_proto(cls, proto_msg: Bench) -> "BenchmarkMessage":
        return cls(
            len(proto_msg.blob), proto_msg.blob, proto_msg.creation_timestamp_ns, Bench
        )


class BaseSubscriber:
    def receive(self) -> Tuple[BenchmarkMessage, float, float]:
        """
        Block until the next message arrives.
        Returns (BenchmarkMessage, handle_ms, decode_ms).
        """
        raise NotImplementedError

    def msg_type(self) -> type:
        raise NotImplementedError

    def close(self) -> None:
        """Cleanup resources if necessary."""
        pass


class LcmSubscriber(BaseSubscriber):
    def __init__(self, url: str, channel: str):
        self._conn = LCM(provider=url)
        self._last_data: bytes = b""
        self._conn.subscribe(channel, self._callback)
        # TODO: how do I handle if publisher is started after subscriber?
        handshake = LCMHandshake(url, channel)
        handshake.send_ready()

    def _callback(self, _: str, data: bytes) -> None:
        self._last_data = data

    def receive(self) -> Tuple[BenchmarkMessage, float, float]:
        t0 = perf_counter()
        self._conn.handle()  # blocks until _last_data set
        handle_ms = (perf_counter() - t0) * 1e3

        t1 = perf_counter()
        raw = bench_t.decode(self._last_data)
        decode_ms = (perf_counter() - t1) * 1e3

        return BenchmarkMessage.from_lcm(raw), handle_ms, decode_ms

    def msg_type(self) -> type:
        return bench_t


class eCALSubscriber(BaseSubscriber):
    def __init__(self, channel: str):
        ecal_core.initialize(sys.argv, f"benchmark_subscriber_{channel}")
        # NOTE: We purposefully do not use ProtoSubscriber so that we can
        #       measure the decode time directly by doing it ourselves
        # self._sub = ProtoSubscriber(channel, Bench)
        self._sub = ecal_core.subscriber(channel, "proto:" + Bench.DESCRIPTOR.full_name)
        self._queue = Queue(maxsize=100)
        self._sub.set_callback(self._callback)

    def _callback(self, topic: str, msg: bytes, timestamp: float) -> None:
        logger.debug(f"[{topic}] Received message")
        try:
            self._queue.put_nowait(msg)
        except QueueFull:
            logger.error("queue is full")

    def receive(self) -> Tuple[BenchmarkMessage, float, float]:
        t0 = perf_counter()
        raw_msg: bytes = self._queue.get(block=True)
        handle_ms = (perf_counter() - t0) * 1e3

        t1 = perf_counter()
        msg: Bench = Bench()
        msg.ParseFromString(raw_msg)
        decode_ms = (perf_counter() - t1) * 1e3

        return BenchmarkMessage.from_proto(msg), handle_ms, decode_ms

    def msg_type(self) -> type:
        return Bench

    def close(self) -> None:
        ecal_core.finalize()


def main(
    middleware: str,
    lcm_url: str,
    channel_name: str,
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
        f"Starting subscriber ({middleware}): channel={channel_name!r}, expecting {num_msgs} msgs"
    )

    assert middleware in ("lcm", "ecal"), "middleware must be 'lcm' or 'ecal'"
    assert channel_name, "channel_name must not be empty"
    assert num_msgs > 0, "num_msgs must be > 0"

    if isinstance(results_dir, str):
        results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    if middleware == "lcm":
        subscriber: BaseSubscriber = LcmSubscriber(lcm_url, channel_name)
    elif middleware == "ecal":
        subscriber = eCALSubscriber(channel_name)
    else:
        raise ValueError(f"{middleware} not supported")

    handle_durs_ms: List[float] = []
    decode_durs_ms: List[float] = []
    oneway_latency_durs_ms: List[float] = []
    sizes: List[int] = []
    creation_timestamps_s: List[float] = []

    for i in range(num_msgs):
        bm, handle_ms, decode_ms = subscriber.receive()
        oneway_latency_ms = (time_ns() - bm.creation_time_ns) / 1e6

        logger.info(
            f"{'(ignoring first message in saved report)' if i == 0 else ''} "
            f"Received msg {i+1}/{num_msgs}: ({bm.num_bytes} bytes) (creation_time_ns={bm.creation_time_ns}) "
            f"decode msg took {decode_ms:.3f} ms, handle msg took {handle_ms:.3f} ms, one way latency: {oneway_latency_ms:.3f} ms "
        )

        if i != 0:
            # NOTE: we do not "count" first message durations in reported statistics as it includes
            #       extra overhead that the other messages don't have
            handle_durs_ms.append(handle_ms)
            decode_durs_ms.append(decode_ms)

            oneway_latency_durs_ms.append(oneway_latency_ms)
            sizes.append(bm.num_bytes)
            creation_timestamps_s.append(bm.creation_time_ns / 1e9)

    subscriber.close()

    handle_stats = compute_stats(handle_durs_ms, "ms")
    decode_stats = compute_stats(decode_durs_ms, "ms")
    oneway_latency_stats = compute_stats(oneway_latency_durs_ms, "ms")
    size_stats = compute_stats(sizes, "bytes")

    processing_rates_hz = [
        1.0 / (t2 - t1)
        for t1, t2 in zip(creation_timestamps_s, creation_timestamps_s[1:])
        if (t2 - t1) > 0
    ]
    processing_rate_stats = compute_stats(processing_rates_hz, "hz")

    report: Dict[str, Any] = {
        "timestamp_us": int(now() * 1e6),
        "parameters": {
            "middleware": middleware,
            "channel_name": channel_name,
            "num_msgs": num_msgs,
            "message_type": str(subscriber.msg_type()),
        },
        "handle_durations_ms": handle_durs_ms,
        "handle_duration_statistics": handle_stats,
        "decode_durations_ms": decode_durs_ms,
        "decode_duration_statistics": decode_stats,
        "oneway_latencies_ms": oneway_latency_durs_ms,
        "oneway_latency_statistics": oneway_latency_stats,
        "num_bytes_list": sizes,
        "num_bytes_statistics": size_stats,
        "processing_rates_hz": processing_rates_hz,
        "processing_rate_statistics": processing_rate_stats,
    }

    out = (
        results_dir
        / f"{middleware}_subscriber_benchmark_report_{report['timestamp_us']}.yaml"
    )
    with open(out, "w") as f:
        yaml.dump(report, f)
    logger.info(f"Wrote report to {out}")


if __name__ == "__main__":
    parser = ArgumentParser(description="Benchmark LCM or eCAL subscription processing")
    parser.add_argument("--middleware", choices=("lcm", "ecal"), default="lcm")
    parser.add_argument(
        "--lcm-url", type=str, default="udpm://239.255.76.67:7667?ttl=1"
    )
    parser.add_argument("--channel-name", type=str, default="/benchmark")
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
        num_msgs=args.num_msgs,
        results_dir=args.results_dir,
        log_level=args.log_level,
        log_output=args.log_output,
    )
