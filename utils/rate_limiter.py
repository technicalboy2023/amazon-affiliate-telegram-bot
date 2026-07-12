"""
In-memory async rate limiter using sliding window.

No Redis needed -- works within a single process.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter.

    Usage:
        limiter = RateLimiter(max_calls=20, period=60.0)
        async with limiter.acquire("bot_post"):
            await send_message(...)
    """

    def __init__(self, max_calls: int, period: float = 60.0):
        """
        Args:
            max_calls: Maximum number of calls allowed in the period.
            period: Time window in seconds.
        """
        self.max_calls = max_calls
        self.period = period
        self._timestamps: dict[str, list[float]] = defaultdict(list)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def wait(self, key: str = "default") -> None:
        """Wait until a call is allowed under the rate limit."""
        async with self._locks[key]:
            now = time.monotonic()
            timestamps = self._timestamps[key]

            # Remove expired timestamps
            cutoff = now - self.period
            self._timestamps[key] = [t for t in timestamps if t > cutoff]
            timestamps = self._timestamps[key]

            if len(timestamps) >= self.max_calls:
                # Calculate wait time until the oldest timestamp expires
                wait_time = timestamps[0] - cutoff
                if wait_time > 0:
                    logger.debug("Rate limit hit for '%s'. Waiting %.2fs", key, wait_time)
                    await asyncio.sleep(wait_time)
                    # Clean up again after waiting
                    now = time.monotonic()
                    cutoff = now - self.period
                    self._timestamps[key] = [t for t in self._timestamps[key] if t > cutoff]

            self._timestamps[key].append(time.monotonic())

    class _AcquireContext:
        """Async context manager for rate limiting."""

        def __init__(self, limiter: RateLimiter, key: str):
            self._limiter = limiter
            self._key = key

        async def __aenter__(self):
            await self._limiter.wait(self._key)
            return self

        async def __aexit__(self, *exc_info):
            pass

    def acquire(self, key: str = "default") -> _AcquireContext:
        """Return an async context manager that waits for rate limit."""
        return self._AcquireContext(self, key)
