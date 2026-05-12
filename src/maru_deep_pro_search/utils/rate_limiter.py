"""Rate limiting and circuit breaker utilities for search engines."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Token-bucket-like rate limiter with a sliding window.

    Args:
        max_requests: Maximum number of requests allowed in the window.
        window_seconds: Time window in seconds.
    """

    max_requests: int = 10
    window_seconds: float = 60.0
    _requests: list[float] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self, wait: bool = True) -> bool:
        """Acquire permission to make a request.

        Returns True if allowed, False if the limit is reached and
        ``wait`` is False.
        """
        async with self._lock:
            now = time.monotonic()
            # Drop requests outside the window
            cutoff = now - self.window_seconds
            self._requests = [t for t in self._requests if t > cutoff]

            if len(self._requests) < self.max_requests:
                self._requests.append(now)
                return True

            if not wait:
                return False

            # Wait until the oldest request slides out of the window
            sleep_time = self._requests[0] + self.window_seconds - now
            if sleep_time > 0:
                logger.debug("Rate limit hit, sleeping %.2fs", sleep_time)
                await asyncio.sleep(sleep_time)

            now = time.monotonic()
            self._requests = [t for t in self._requests if t > cutoff]
            self._requests.append(now)
            return True


class CircuitBreaker:
    """Circuit breaker for search engines.

    Opens after ``failure_threshold`` consecutive failures and stays
    open for ``recovery_seconds``. This prevents hammering a blocked
    engine with retries.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_seconds: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed | open | half_open
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        async with self._lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if time.monotonic() - self._last_failure_time > self.recovery_seconds:
                    self._state = "half_open"
                    logger.debug("Circuit breaker entering half-open state")
                    return True
                return False
            # half_open
            return True

    async def record_success(self):
        async with self._lock:
            self._failure_count = 0
            if self._state in ("open", "half_open"):
                self._state = "closed"
                logger.debug("Circuit breaker closed after success")

    async def record_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                if self._state != "open":
                    self._state = "open"
                    logger.warning(
                        "Circuit breaker OPENED after %d consecutive failures",
                        self._failure_count,
                    )

    @property
    def state(self) -> str:
        return self._state
