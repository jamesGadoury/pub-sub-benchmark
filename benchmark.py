import os
from contextlib import ContextDecorator
from random import getrandbits
from time import sleep, time, time_ns
from typing import Dict, List, Optional

import ecal.core.core as ecal_core
import lcm
from bench_pb2 import Bench
from lcmtypes import bench_t, handshake_t
from numpy import mean, percentile, std


class LCMHandshake:
    """
    LCM “who’s there?” handshake helper.

      - Subscriber calls send_ready() once it’s set up.
      - Publisher polls has_subscriber() or blocks in wait_for_subscriber().
    """

    def __init__(self, url: str, channel: str):
        """
        :param url:     LCM provider URL (e.g. "udpm://239.255.76.67:7667?ttl=1")
        :param channel: the base data channel, e.g. "/benchmark"
        """
        self._conn = lcm.LCM(provider=url)
        self._channel = channel
        self._ready_chan = f"{channel}_ready"
        self._got_ready = False

        # subscribe to “<channel>_ready” and flip the flag
        self._conn.subscribe(self._ready_chan, self._on_ready)

    def _on_ready(self, topic: str, data: bytes) -> None:
        # we don’t need to parse the payload—
        # the arrival of any message is enough
        self._got_ready = True

    def send_ready(self) -> None:
        """Subscriber: fire off 1–2 “I’m here” pings."""
        msg = handshake_t()
        msg.pid = os.getpid()
        self._conn.publish(self._ready_chan, msg.encode())
        # send twice in case the publisher isn't yet subscribed:
        sleep(0.01)
        self._conn.publish(self._ready_chan, msg.encode())

    def has_subscriber(self) -> bool:
        """Non-blocking: has any ready-ping arrived yet?"""
        return self._got_ready

    def wait_for_subscriber(self, timeout_s: Optional[float] = None) -> bool:
        """
        Blocking: spin until has_subscriber() is True or timeout elapses.
        :param timeout_s: seconds to wait (None = forever)
        :returns: True if a subscriber announced itself, False on timeout
        """
        if timeout_s is None:
            # will block until the next ready-ping arrives
            self._conn.handle()
        else:
            self._conn.handle_timeout(int(timeout_s * 1e3))
        return self._got_ready


class eCALMonitor(ContextDecorator):
    def __init__(self):
        pass

    def __enter__(self):
        ecal_core.mon_initialize()
        return self

    def __exit__(self, exc_type, exc, tb):
        ecal_core.mon_finalize()
        # swallow nothing: let exceptions propagate
        return False

    @classmethod
    def has_subscriber(cls, topic: str) -> bool:
        state, mon = ecal_core.mon_monitoring()
        if state != 0 or not mon:
            return False
        for mon_topic in mon.get("topics", []):
            if mon_topic["direction"] == "subscriber" and mon_topic["tname"] == topic:
                return True
        return False


def generate_lcm_benchmark_msg(num_bytes: int) -> bench_t:
    """
    Create an lcm bench_t message with a random blob of length num_bytes.
    """
    if not (0 < num_bytes <= 4_294_967_296):
        raise ValueError("num_bytes must be in (0, 4294967296]")

    msg = bench_t()
    msg.num_bytes = num_bytes
    msg.blob = bytes([getrandbits(8) for _ in range(num_bytes)])
    msg.creation_timestamp_ns = time_ns()

    return msg


def generate_proto_benchmark_msg(num_bytes: int) -> Bench:
    """
    Create a proto Bench message with a random blob of length num_bytes.
    """
    if not (0 < num_bytes <= 4_294_967_296):
        raise ValueError("num_bytes must be in (0, 4294967296]")

    msg = Bench()
    msg.blob = bytes(getrandbits(8) for _ in range(num_bytes))
    msg.creation_timestamp_ns = time_ns()

    return msg


def compute_stats(sample: List[float] | List[int], units: str) -> Dict[str, float]:
    """
    Given a list of examples in specified units, return
    min, max, p50, p90, p95.
    """
    if not sample:
        raise ValueError("sample list must not be empty")

    return {
        f"min_{units}": min(sample),
        f"max_{units}": max(sample),
        f"mean_{units}": float(mean(sample)),
        f"stddev_{units}": float(std(sample)),
        f"p50_{units}": float(percentile(sample, 50)),
        f"p90_{units}": float(percentile(sample, 90)),
        f"p95_{units}": float(percentile(sample, 95)),
    }
