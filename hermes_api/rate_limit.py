"""Simple process-local rate limiting for the Hermes API."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, status


class RateLimiter:
    """Fixed-window process-local limiter keyed by client identity."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, *, key: str, limit_per_minute: int) -> None:
        """Raise 429 when *key* exceeds the configured per-minute limit."""

        if limit_per_minute <= 0:
            return

        now = time.monotonic()
        window_start = now - 60
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < window_start:
                hits.popleft()
            if len(hits) >= limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            hits.append(now)


rate_limiter = RateLimiter()
