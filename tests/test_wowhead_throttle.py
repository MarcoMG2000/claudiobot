"""Tests for RateLimiter throttling (Slice A): R8, R9, R11.

Deterministic and network-free: a fake clock (a list of timestamps) and a spy
sleep are injected (R11), so the throttle logic is verified without any
wall-clock time and without real sleeping.
"""

from __future__ import annotations

from wowrag.ingest.wowhead import RateLimiter


class _FakeClock:
    """Returns successive timestamps from a predefined list (R11)."""

    def __init__(self, times: list[float]) -> None:
        self._times = list(times)
        self._i = 0

    def __call__(self) -> float:
        value = self._times[self._i]
        self._i += 1
        return value


class _SpySleep:
    """Records every requested sleep duration without sleeping (R11)."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


# ---------------------------------------------------------------------------
# R8: the first acquire never waits
# ---------------------------------------------------------------------------


def test_first_acquire_no_wait():  # R8
    """The very first acquire() call does not sleep."""
    sleep = _SpySleep()
    # Two clock reads: one at entry, one to record _last.
    limiter = RateLimiter(1.0, clock=_FakeClock([100.0, 100.0]), sleep=sleep)
    limiter.acquire()
    assert sleep.calls == []


# ---------------------------------------------------------------------------
# R9: a second acquire within the interval sleeps the exact difference
# ---------------------------------------------------------------------------


def test_second_acquire_within_interval_sleeps():  # R9
    """A second acquire 0.3s after the first sleeps the remaining 0.7s."""
    sleep = _SpySleep()
    # acquire #1: clock -> 100.0 (now), 100.0 (record _last)
    # acquire #2: clock -> 100.3 (now), <post-sleep> 101.0 (record _last)
    clock = _FakeClock([100.0, 100.0, 100.3, 101.0])
    limiter = RateLimiter(1.0, clock=clock, sleep=sleep)
    limiter.acquire()
    limiter.acquire()
    assert len(sleep.calls) == 1
    assert abs(sleep.calls[0] - 0.7) < 1e-9  # R9: min_interval - elapsed


# ---------------------------------------------------------------------------
# R9: a second acquire after the interval does not sleep
# ---------------------------------------------------------------------------


def test_second_acquire_after_interval_no_wait():  # R9
    """A second acquire after >= min_interval has elapsed does not sleep."""
    sleep = _SpySleep()
    clock = _FakeClock([100.0, 100.0, 102.0, 102.0])
    limiter = RateLimiter(1.0, clock=clock, sleep=sleep)
    limiter.acquire()
    limiter.acquire()
    assert sleep.calls == []


# ---------------------------------------------------------------------------
# R11: the limiter uses the injected clock, never wall-clock time
# ---------------------------------------------------------------------------


def test_acquire_uses_injected_clock():  # R11
    """The limiter reads time only from the injected clock (no wall clock)."""
    reads: list[float] = []

    def clock() -> float:
        reads.append(0.0)
        return 0.0

    limiter = RateLimiter(1.0, clock=clock, sleep=_SpySleep())
    limiter.acquire()
    # The first acquire reads the injected clock at least once.
    assert len(reads) >= 1
