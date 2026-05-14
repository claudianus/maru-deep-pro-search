"""Tests for retry utilities with exponential backoff."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from maru_deep_pro_search.exceptions import MaruSearchError
from maru_deep_pro_search.utils.retry import with_retry


class TestWithRetry:
    """Tests for with_retry async decorator."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self) -> None:
        mock_fn = AsyncMock(return_value="success")
        result = await with_retry(mock_fn)
        assert result == "success"
        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_success(self) -> None:
        mock_fn = AsyncMock(side_effect=[ValueError("fail"), "success"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(mock_fn, max_attempts=3, base_delay=0.1)
        assert result == "success"
        assert mock_fn.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self) -> None:
        mock_fn = AsyncMock(side_effect=ValueError("fail"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="fail"):
                await with_retry(mock_fn, max_attempts=2, base_delay=0.1)
        assert mock_fn.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_maru_error_raises_immediately(self) -> None:
        exc = MaruSearchError("blocked", retryable=False)
        mock_fn = AsyncMock(side_effect=exc)
        with pytest.raises(MaruSearchError, match="blocked"):
            await with_retry(mock_fn, max_attempts=3)
        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_retryable_maru_error_gets_retried(self) -> None:
        exc = MaruSearchError("timeout", retryable=True)
        mock_fn = AsyncMock(side_effect=[exc, "success"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(mock_fn, max_attempts=3, base_delay=0.1)
        assert result == "success"
        assert mock_fn.call_count == 2

    @pytest.mark.asyncio
    async def test_zero_max_attempts_raises_runtime_error(self) -> None:
        mock_fn = AsyncMock(return_value="success")
        with pytest.raises(RuntimeError, match="All retry attempts exhausted"):
            await with_retry(mock_fn, max_attempts=0)

    @pytest.mark.asyncio
    async def test_specific_exception_type_only(self) -> None:
        mock_fn = AsyncMock(side_effect=[ValueError("fail"), "success"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="fail"):
                await with_retry(
                    mock_fn, max_attempts=2, base_delay=0.1, retryable_exceptions=(RuntimeError,)
                )

    @pytest.mark.asyncio
    async def test_logs_warning_on_retry(self) -> None:
        mock_fn = AsyncMock(side_effect=[ValueError("fail"), "success"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("maru_deep_pro_search.utils.retry.logger") as mock_logger:
                await with_retry(mock_fn, max_attempts=2, base_delay=0.1)
        mock_logger.warning.assert_called_once()
        fmt, attempt, max_a, name, exc, delay = mock_logger.warning.call_args[0]
        assert attempt == 1
        assert max_a == 2

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self) -> None:
        mock_fn = AsyncMock(return_value="ok")
        await with_retry(mock_fn, "arg1", key="val", max_attempts=1)
        mock_fn.assert_called_once_with("arg1", key="val")

    @pytest.mark.asyncio
    async def test_delay_with_jitter(self) -> None:
        mock_fn = AsyncMock(side_effect=[ValueError("fail"), "success"])
        with patch("maru_deep_pro_search.utils.retry.random.random", return_value=0.5):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await with_retry(mock_fn, max_attempts=2, base_delay=1.0, max_delay=10.0)
        mock_sleep.assert_called_once()
        # delay = min(1.0 * 2^0, 10.0) = 1.0
        # jitter = 1.0 * 0.3 * (0.5 * 2 - 1) = 1.0 * 0.3 * 0 = 0
        # actual_delay = max(0.1, 1.0 + 0) = 1.0
        assert mock_sleep.call_args[0][0] == pytest.approx(1.0, abs=0.01)
