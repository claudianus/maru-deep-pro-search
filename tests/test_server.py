"""Tests for MCP server layer (decorators, utilities, tool delegation)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from maru_deep_pro_search.server import (
    _consume_update_notice,
    _get_session_id,
    _inject_notice_into_response,
    _with_audit,
    _with_enforcement,
    _with_validation,
)

# ── Update notice utilities ─────────────────────────────────────


class TestUpdateNotice:
    def test_consume_returns_none_when_no_notice(self) -> None:
        assert _consume_update_notice() is None

    def test_inject_passes_through_when_no_notice(self) -> None:
        assert _inject_notice_into_response("hello") == "hello"

    def test_inject_prepends_notice_once(self, monkeypatch: Any) -> None:
        from maru_deep_pro_search import server as srv

        srv._pending_update_notice = "NEW VERSION"
        srv._update_notice_shown = False
        result = _inject_notice_into_response("body")
        assert result == "NEW VERSION\n\nbody"
        assert _consume_update_notice() is None
        # Reset
        srv._pending_update_notice = None
        srv._update_notice_shown = False


# ── Session ID extraction ───────────────────────────────────────


class TestGetSessionId:
    def test_none_returns_unknown(self) -> None:
        assert _get_session_id(None) == "unknown"

    def test_client_id(self) -> None:
        ctx = MagicMock()
        ctx.client_id = "abc-123"
        assert _get_session_id(ctx) == "abc-123"

    def test_fallback_to_request_id(self) -> None:
        ctx = MagicMock()
        ctx.client_id = None
        ctx.request_id = "req-456"
        assert _get_session_id(ctx) == "req-456"


# ── Validation decorator ────────────────────────────────────────


class TestWithValidation:
    @pytest.mark.asyncio
    async def test_query_too_long(self) -> None:
        async def dummy(**kwargs):
            return "ok"

        wrapped = _with_validation("test")(dummy)
        with pytest.raises(ValueError, match="Query exceeds maximum length"):
            await wrapped(query="x" * 4097)

    @pytest.mark.asyncio
    async def test_urls_too_many(self) -> None:
        async def dummy(**kwargs):
            return "ok"

        wrapped = _with_validation("test")(dummy)
        with pytest.raises(ValueError, match="Maximum 50 URLs"):
            await wrapped(urls=["http://a"] * 51)

    @pytest.mark.asyncio
    async def test_queries_too_many(self) -> None:
        async def dummy(**kwargs):
            return "ok"

        wrapped = _with_validation("test")(dummy)
        with pytest.raises(ValueError, match="Maximum 10 queries"):
            await wrapped(queries=["q"] * 11)

    @pytest.mark.asyncio
    async def test_valid_input_passes_through(self) -> None:
        async def dummy(**kwargs):
            return "ok"

        wrapped = _with_validation("test")(dummy)
        assert await wrapped(query="short", urls=["http://a"], queries=["q"]) == "ok"


# ── Audit decorator ─────────────────────────────────────────────


class TestWithAudit:
    @pytest.mark.asyncio
    async def test_logs_success(self, monkeypatch: Any) -> None:
        logged = {}
        mock_logger = MagicMock()
        mock_logger.log_tool_call = lambda **kw: logged.update(kw)
        monkeypatch.setattr(
            "maru_deep_pro_search.harness.audit.AuditLogger",
            lambda: mock_logger,
        )

        async def dummy(**kwargs):
            return "result"

        wrapped = _with_audit("my_tool")(dummy)
        result = await wrapped(ctx=None)
        assert result == "result"
        assert logged["tool_name"] == "my_tool"
        assert logged["result_preview"] == "result"

    @pytest.mark.asyncio
    async def test_logs_exception_and_re_raises(self, monkeypatch: Any) -> None:
        logged = {}
        mock_logger = MagicMock()
        mock_logger.log_tool_call = lambda **kw: logged.update(kw)
        monkeypatch.setattr(
            "maru_deep_pro_search.harness.audit.AuditLogger",
            lambda: mock_logger,
        )

        async def dummy(**kwargs):
            raise RuntimeError("boom")

        wrapped = _with_audit("my_tool")(dummy)
        with pytest.raises(RuntimeError, match="boom"):
            await wrapped(ctx=None)
        assert "ERROR: boom" in logged.get("result_preview", "")


# ── Enforcement decorator ───────────────────────────────────────


class TestWithEnforcement:
    @pytest.mark.asyncio
    async def test_deep_research_marks_done(self, monkeypatch: Any) -> None:
        from unittest.mock import AsyncMock

        enforcer = MagicMock()
        enforcer.mark_research_done = AsyncMock()
        monkeypatch.setattr(
            "maru_deep_pro_search.harness.enforcer.get_enforcer",
            lambda: enforcer,
        )

        async def dummy(*args, **kwargs):
            return "research result"

        wrapped = _with_enforcement("deep_research")(dummy)
        result = await wrapped("my query", ctx=None)
        assert result == "research result"
        enforcer.mark_research_done.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_other_tools_check_research(self, monkeypatch: Any) -> None:
        from unittest.mock import AsyncMock

        enforcer = MagicMock()
        enforcer.check_research = AsyncMock()
        monkeypatch.setattr(
            "maru_deep_pro_search.harness.enforcer.get_enforcer",
            lambda: enforcer,
        )

        async def dummy(**kwargs):
            return "ok"

        wrapped = _with_enforcement("fetch_page")(dummy)
        await wrapped(ctx=None)
        enforcer.check_research.assert_awaited_once()


# ── always_research_first prompt ────────────────────────────────


class TestPrompts:
    def test_always_research_first_returns_non_empty(self) -> None:
        from maru_deep_pro_search.server import always_research_first

        text = always_research_first()
        assert "MANDATORY" in text
        assert "deep_research" in text
