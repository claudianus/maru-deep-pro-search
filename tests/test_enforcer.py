"""Tests for the session enforcement engine."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from maru_deep_pro_search.harness.enforcer import (
    CodeGenerationBlockedError,
    ResearchRequiredError,
    SessionEnforcer,
    SessionState,
    get_enforcer,
)


class TestSessionState:
    def test_defaults(self) -> None:
        state = SessionState(session_id="test-1")
        assert state.session_id == "test-1"
        assert state.research_done is False
        assert state.research_id == ""
        assert state.citations_found == []
        assert state.tools_called == []

    def test_record_tool(self) -> None:
        state = SessionState(session_id="test-1")
        state.record_tool("deep_research")
        state.record_tool("web_search")
        assert state.tools_called == ["deep_research", "web_search"]

    def test_mark_research(self) -> None:
        state = SessionState(session_id="test-1")
        state.mark_research("python asyncio", "Result with [1] and [2]")
        assert state.research_done is True
        assert state.research_query == "python asyncio"
        assert state.research_result == "Result with [1] and [2]"
        assert state.citations_found == ["1", "2"]
        assert state.research_id.startswith("RSCH-")
        assert len(state.research_id) == 17  # RSCH- + 12 hex chars

    def test_research_age_before_marked(self) -> None:
        state = SessionState(session_id="test-1")
        assert state.research_age_seconds == float("inf")

    def test_research_age_after_marked(self) -> None:
        state = SessionState(session_id="test-1")
        state.mark_research("q", "r")
        assert state.research_age_seconds < 1.0

    def test_is_fresh_immediately(self) -> None:
        state = SessionState(session_id="test-1")
        state.mark_research("q", "r")
        assert state.is_fresh is True

    def test_is_fresh_after_stale(self) -> None:
        state = SessionState(session_id="test-1")
        state.mark_research("q", "r")
        # Simulate 31 minutes passing
        state.research_timestamp = time.time() - 1860
        assert state.is_fresh is False


class TestSessionEnforcer:
    @pytest.fixture
    def enforcer(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SessionEnforcer:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        return SessionEnforcer()

    def test_get_or_create(self, enforcer: SessionEnforcer) -> None:
        state1 = enforcer.get_or_create("sess-a")
        state2 = enforcer.get_or_create("sess-a")
        assert state1 is state2
        assert state1.session_id == "sess-a"

    @pytest.mark.asyncio
    async def test_mark_research_done(self, enforcer: SessionEnforcer) -> None:
        state = await enforcer.mark_research_done("sess-a", "query", "result [1]")
        assert state.research_done is True
        assert state.research_query == "query"
        assert state.citations_found == ["1"]
        # Marker files created
        assert (Path.home() / ".maru" / "last_research").exists()
        assert (Path.home() / ".maru" / "session_research.json").exists()

    @pytest.mark.asyncio
    async def test_check_research_exempt_tool(self, enforcer: SessionEnforcer) -> None:
        state = await enforcer.check_research("sess-a", "deep_research")
        assert state.session_id == "sess-a"

    @pytest.mark.asyncio
    async def test_check_research_blocks_when_not_done(self, enforcer: SessionEnforcer) -> None:
        with pytest.raises(ResearchRequiredError):
            await enforcer.check_research("sess-a", "generate_code")

    @pytest.mark.asyncio
    async def test_check_research_blocks_when_stale(self, enforcer: SessionEnforcer) -> None:
        state = await enforcer.mark_research_done("sess-a", "q", "r")
        state.research_timestamp = time.time() - 1860
        with pytest.raises(ResearchRequiredError) as exc:
            await enforcer.check_research("sess-a", "generate_code")
        assert "expired" in str(exc.value)

    @pytest.mark.asyncio
    async def test_check_research_allows_when_fresh(self, enforcer: SessionEnforcer) -> None:
        await enforcer.mark_research_done("sess-a", "q", "r")
        state = await enforcer.check_research("sess-a", "generate_code")
        assert state.session_id == "sess-a"

    @pytest.mark.asyncio
    async def test_validate_code_generation_no_research(self, enforcer: SessionEnforcer) -> None:
        with pytest.raises(CodeGenerationBlockedError) as exc:
            await enforcer.validate_code_generation("sess-a", "RSCH-123", "code")
        assert "no research" in str(exc.value)

    @pytest.mark.asyncio
    async def test_validate_code_generation_stale(self, enforcer: SessionEnforcer) -> None:
        state = await enforcer.mark_research_done("sess-a", "q", "r [1]")
        state.research_timestamp = time.time() - 1860
        with pytest.raises(CodeGenerationBlockedError) as exc:
            await enforcer.validate_code_generation("sess-a", state.research_id, "code")
        assert "stale" in str(exc.value)

    @pytest.mark.asyncio
    async def test_validate_code_generation_wrong_id(self, enforcer: SessionEnforcer) -> None:
        await enforcer.mark_research_done("sess-a", "q", "r [1]")
        with pytest.raises(CodeGenerationBlockedError) as exc:
            await enforcer.validate_code_generation("sess-a", "WRONG-ID", "code")
        assert "mismatch" in str(exc.value)

    @pytest.mark.asyncio
    async def test_validate_code_generation_no_citations(self, enforcer: SessionEnforcer) -> None:
        state = await enforcer.mark_research_done("sess-a", "q", "r [1]")
        report = await enforcer.validate_code_generation(
            "sess-a", state.research_id, "code without citations"
        )
        assert report["passed"] is False
        assert report["code_citations"] == []

    @pytest.mark.asyncio
    async def test_validate_code_generation_valid(self, enforcer: SessionEnforcer) -> None:
        state = await enforcer.mark_research_done("sess-a", "q", "r [1] [2]")
        report = await enforcer.validate_code_generation("sess-a", state.research_id, "code [1]")
        assert report["passed"] is True
        assert report["code_citations"] == ["1"]
        assert report["research_citations"] == ["1", "2"]
        assert report["missing_citations"] == []

    @pytest.mark.asyncio
    async def test_validate_code_generation_missing_citation(
        self, enforcer: SessionEnforcer
    ) -> None:
        state = await enforcer.mark_research_done("sess-a", "q", "r [1]")
        report = await enforcer.validate_code_generation(
            "sess-a", state.research_id, "code [1] [99]"
        )
        assert report["passed"] is False
        assert report["missing_citations"] == ["99"]

    @pytest.mark.asyncio
    async def test_session_summary(self, enforcer: SessionEnforcer) -> None:
        await enforcer.mark_research_done("sess-a", "q", "r")
        summary = await enforcer.session_summary("sess-a")
        assert summary["session_id"] == "sess-a"
        assert summary["research_done"] is True
        assert summary["research_query"] == "q"
        assert summary["is_fresh"] is True
        assert "research_id" in summary

    @pytest.mark.asyncio
    async def test_prune_stale_sessions(self, enforcer: SessionEnforcer) -> None:
        enforcer.get_or_create("fresh")
        enforcer.get_or_create("stale")
        # Make stale session old
        enforcer._sessions["stale"].created_at = time.time() - 7200
        removed = await enforcer.prune_stale_sessions(max_age_seconds=3600)
        assert removed == 1
        assert "stale" not in enforcer._sessions
        assert "fresh" in enforcer._sessions

    @pytest.mark.asyncio
    async def test_prune_keeps_fresh(self, enforcer: SessionEnforcer) -> None:
        enforcer.get_or_create("fresh")
        removed = await enforcer.prune_stale_sessions()
        assert removed == 0
        assert "fresh" in enforcer._sessions


class TestGetEnforcer:
    def test_singleton(self) -> None:
        e1 = get_enforcer()
        e2 = get_enforcer()
        assert e1 is e2
