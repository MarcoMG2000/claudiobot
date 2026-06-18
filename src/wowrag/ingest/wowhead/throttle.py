"""RateLimiter: enforces a minimum interval between successive requests (R8, R9).

The clock and ``sleep`` are INJECTABLE (R11), defaulting to ``time.monotonic`` /
``time.sleep``. Tests pass a fake clock (a deterministic timestamp source) and a
spy ``sleep`` so the throttle logic is verifiable without any wall-clock time.
No global state — each instance tracks its own last-request time.
"""

from __future__ import annotations

import time
from typing import Callable


class RateLimiter:
    """Enforces a minimum interval between successive ``acquire()`` calls.

    Call ``acquire()`` immediately before each real HTTP GET in the pipeline
    (R8). The first call never waits; if fewer than ``min_interval_s`` have
    elapsed since the previous call, it sleeps the difference (R9).

    Parameters
    ----------
    min_interval_s:
        Minimum seconds between successive requests (from ``Settings``, R8).
    clock:
        Injectable monotonic time source (R11). Default: ``time.monotonic``.
    sleep:
        Injectable sleep function (R11). Default: ``time.sleep``.
    """

    def __init__(
        self,
        min_interval_s: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def acquire(self) -> None:
        """Block until at least ``min_interval_s`` have passed since the last call.

        The first call returns immediately (R8). A subsequent call within the
        interval sleeps the remaining time via the injected ``sleep`` (R9).
        """
        now = self._clock()
        if self._last is not None:
            wait = self._min - (now - self._last)
            if wait > 0:
                self._sleep(wait)  # R9: throttle
        self._last = self._clock()
