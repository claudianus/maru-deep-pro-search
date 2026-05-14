"""Tests for rate limiting and circuit breaker utilities."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from maru_deep_pro_search.utils.rate_limiter import CircuitBreaker, RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter token-bucket-like rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_initially_allowed(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60.0)
        result = await limiter.acquire(wait=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_exceeds_limit_without_wait(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60.0)
        assert await limiter.acquire(wait=False) is True
        assert await limiter.acquire(wait=False) is True
        assert await limiter.acquire(wait=False) is False

    @pytest.mark.asyncio
    async def test_acquire_exceeds_limit_with_wait(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=0.05)
        assert await limiter.acquire(wait=False) is True
        # Wait for window to slide
        await asyncio.sleep(0.06)
        assert await limiter.acquire(wait=True) is True

    @pytest.mark.asyncio
    async def test_acquire_waits_until_window_slides(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)
        assert await limiter.acquire(wait=False) is True

        start = time.monotonic()
        assert await limiter.acquire(wait=True) is True
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08  # should have waited roughly window_seconds

    @pytest.mark.asyncio
    async def test_acquire_expires_old_requests(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=0.05)
        assert await limiter.acquire(wait=False) is True
        await asyncio.sleep(0.06)
        # Old request should have expired, so new one is allowed
        assert await limiter.acquire(wait=False) is True

    @pytest.mark.asyncio
    async def test_acquire_multiple_within_window(self) -> None:
        limiter = RateLimiter(max_requests=3, window_seconds=60.0)
        assert await limiter.acquire(wait=False) is True
        assert await limiter.acquire(wait=False) is True
        assert await limiter.acquire(wait=False) is True
        assert await limiter.acquire(wait=False) is False

    @pytest.mark.asyncio
    async def test_acquire_wait_logs_debug(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)
        assert await limiter.acquire(wait=False) is True
        with patch("maru_deep_pro_search.utils.rate_limiter.logger") as mock_logger:
            assert await limiter.acquire(wait=True) is True
            mock_logger.debug.assert_called_once()
            assert "Rate limit hit, sleeping" in mock_logger.debug.call_args[0][0]

    @pytest.mark.asyncio
    async def test_concurrent_acquires_respect_limit(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60.0)

        async def try_acquire():
            return await limiter.acquire(wait=False)

        results = await asyncio.gather(*[try_acquire() for _ in range(5)])
        assert results.count(True) == 2
        assert results.count(False) == 3

    @pytest.mark.asyncio
    async def test_default_values(self) -> None:
        limiter = RateLimiter()
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60.0
        assert await limiter.acquire(wait=False) is True


class TestCircuitBreaker:
    """Tests for CircuitBreaker state machine."""

    @pytest.mark.asyncio
    async def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert await cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_record_failure_increments_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == "closed"
        assert cb._failure_count == 2

    @pytest.mark.asyncio
    async def test_record_failure_opens_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=2)
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == "open"
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_record_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_open_circuit_blocks_execution(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        await cb.record_failure()
        assert cb.state == "open"
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_open_circuit_transitions_to_half_open_after_recovery(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        assert cb.state == "open"
        await asyncio.sleep(0.06)
        assert await cb.can_execute() is True
        assert cb.state == "half_open"

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.06)
        assert await cb.can_execute() is True  # half_open
        await cb.record_success()
        assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.06)
        assert await cb.can_execute() is True  # half_open
        await cb.record_failure()
        assert cb.state == "open"

    @pytest.mark.asyncio
    async def test_record_success_from_open_logs_debug(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.06)
        with patch("maru_deep_pro_search.utils.rate_limiter.logger") as mock_logger:
            await cb.record_success()
            mock_logger.debug.assert_called_once()
            assert "Circuit breaker closed after success" in mock_logger.debug.call_args[0][0]

    @pytest.mark.asyncio
    async def test_record_failure_opens_logs_warning(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        with patch("maru_deep_pro_search.utils.rate_limiter.logger") as mock_logger:
            await cb.record_failure()
            mock_logger.warning.assert_called_once()
            assert "Circuit breaker OPENED" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_half_open_transition_logs_debug(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.06)
        with patch("maru_deep_pro_search.utils.rate_limiter.logger") as mock_logger:
            await cb.can_execute()
            mock_logger.debug.assert_called_once()
            assert "Circuit breaker entering half-open state" in mock_logger.debug.call_args[0][0]

    @pytest.mark.asyncio
    async def test_success_while_closed_does_not_log(self, caplog) -> None:
        caplog.set_level("DEBUG")
        cb = CircuitBreaker()
        await cb.record_success()
        assert "Circuit breaker closed after success" not in caplog.text

    @pytest.mark.asyncio
    async def test_can_execute_half_open_returns_true(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.06)
        assert cb.state == "open"
        result = await cb.can_execute()
        assert result is True
        assert cb.state == "half_open"

    @pytest.mark.asyncio
    async def test_concurrent_can_execute_safe(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        results = await asyncio.gather(*[cb.can_execute() for _ in range(10)])
        # All should see open initially and return False
        assert all(r is False for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_record_failure_safe(self) -> None:
        cb = CircuitBreaker(failure_threshold=10)
        await asyncio.gather(*[cb.record_failure() for _ in range(5)])
        assert cb._failure_count == 5

    @pytest.mark.asyncio
    async def test_custom_threshold_and_recovery(self) -> None:
        cb = CircuitBreaker(failure_threshold=5, recovery_seconds=120.0)
        for _ in range(4):
            await cb.record_failure()
        assert cb.state == "closed"
        await cb.record_failure()
        assert cb.state == "open"

    @pytest.mark.asyncio
    async def test_can_execute_direct_half_open_state(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=60.0)
        cb._state = "half_open"
        assert await cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_record_success_in_open_state(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=60.0)
        await cb.record_failure()
        assert cb.state == "open"
        await cb.record_success()
        assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_record_success_in_half_open_state(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.06)
        await cb.can_execute()  # transitions to half_open
        await cb.record_success()
        assert cb.state == "closed"
