"""Sliding-window rate limiter (requests per minute)."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    def __init__(
        self,
        per_minute: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if per_minute < 1:
            raise ValueError("per_minute must be at least 1")
        self._per_minute = per_minute
        self._clock = clock
        self._sleep = sleep
        self._stamps: deque[float] = deque()

    def wait(self) -> None:
        """Block until a request may be sent, then record it."""
        while True:
            now = self._clock()
            while self._stamps and now - self._stamps[0] >= 60.0:
                self._stamps.popleft()
            if len(self._stamps) < self._per_minute:
                self._stamps.append(now)
                return
            self._sleep(60.0 - (now - self._stamps[0]) + 0.01)
