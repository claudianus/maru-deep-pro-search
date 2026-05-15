"""Session-level enforcement engine — ensures research-before-action.

This is the technical enforcement layer that makes "research first"
a hard gate, not just a suggestion. Every MCP session is tracked,
and tools that depend on research are blocked until deep_research
has been successfully completed.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from ..exceptions import MaruSearchError
from .drift import (
    WorkspaceSnapshot,
    compare_snapshots,
    extract_error_signature,
    format_drift_warning,
    snapshot_workspace,
    suggest_research_queries,
)


class ResearchRequiredError(MaruSearchError):
    """Raised when a tool is called before deep_research in the same session."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"[BLOCKED] '{tool_name}' requires prior deep_research call. "
            f"Run deep_research(query=...) first to unlock this tool.",
            retryable=False,
        )


class CodeGenerationBlockedError(MaruSearchError):
    """Raised when code generation is attempted without research validation."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            f"[BLOCKED] Code generation blocked: {reason} "
            f"Run deep_research(query=...) and use generate_code(research_id=...) "
            f"with valid citations from the research result.",
            retryable=False,
        )


@dataclass
class SessionState:
    """Mutable state tracked per MCP session."""

    session_id: str
    created_at: float = field(default_factory=time.time)
    research_done: bool = False
    research_result: str = ""
    research_query: str = ""
    research_timestamp: float = 0.0
    research_id: str = ""
    tools_called: list[str] = field(default_factory=list)
    citations_found: list[str] = field(default_factory=list)
    code_generated: bool = False
    workspace_snapshot: WorkspaceSnapshot = field(
        default_factory=lambda: WorkspaceSnapshot(root="")
    )
    research_error_signature: str = ""
    last_error_signature: str = ""

    def record_tool(self, name: str, result: str = "") -> None:
        self.tools_called.append(name)
        sig = extract_error_signature(result)
        if sig:
            self.last_error_signature = sig

    def mark_research(self, query: str, result: str) -> None:
        self.research_done = True
        self.research_query = query
        self.research_result = result
        self.research_timestamp = time.time()
        extracted = self._extract_research_id(result)
        self.research_id = extracted or self._generate_research_id()
        self._extract_citations(result)
        self.workspace_snapshot = snapshot_workspace()
        self.research_error_signature = self.last_error_signature

    @staticmethod
    def _extract_research_id(text: str) -> str:
        import re

        match = re.search(r"_research_id:\s*(RSCH-[A-F0-9]+)_", text, re.I)
        return match.group(1).upper() if match else ""

    @staticmethod
    def _generate_research_id() -> str:
        import uuid

        return f"RSCH-{uuid.uuid4().hex[:12].upper()}"

    def _extract_citations(self, text: str) -> None:
        import re

        self.citations_found = re.findall(r"\[(\d+)\]", text)

    @property
    def research_age_seconds(self) -> float:
        if not self.research_timestamp:
            return float("inf")
        return time.time() - self.research_timestamp

    @property
    def is_fresh(self) -> bool:
        """Research is considered stale after 30 minutes."""
        return self.research_age_seconds < 1800


class SessionEnforcer:
    """Tracks every MCP session and enforces research-before-action policies."""

    # Tools that REQUIRE deep_research to have been called first.
    # Tools that can be called WITHOUT prior research.
    RESEARCH_EXEMPT_TOOLS: set[str] = {
        "deep_research",
        "version",
        "list_engines",
        "engine_health",
        "session_state",
        "drift_status",
    }

    # Mid-task enforcement: warn after N non-research tools without fresh research
    MAX_TOOLS_WITHOUT_RESEARCH: int = 5

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    async def mark_research_done(self, session_id: str, query: str, result: str) -> SessionState:
        async with self._lock:
            state = self.get_or_create(session_id)
            state.mark_research(query, result)
            # Also update filesystem markers so client-side hooks can check it
            self._touch_research_marker()
            self._write_session_research_marker(query, state.research_id)
            return state

    @staticmethod
    def _touch_research_marker() -> None:
        """Update the filesystem marker used by client-side hooks."""
        import pathlib

        marker = pathlib.Path.home() / ".maru" / "last_research"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()

    @staticmethod
    def _write_session_research_marker(query: str, research_id: str) -> None:
        """Write a structured session research marker for client-side hooks.

        Aider, Cursor, and other adapters read this file to verify
        research was completed before allowing edits.
        """
        import json
        import pathlib
        from datetime import datetime, timezone

        marker = pathlib.Path.home() / ".maru" / "session_research.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "research_id": research_id,
            "query": query,
        }
        marker.write_text(json.dumps(data, indent=2))

    async def check_research(self, session_id: str, tool_name: str) -> SessionState:
        """Verify that research was done before allowing a dependent tool.

        Raises ResearchRequiredError if research has not been completed.
        """
        state = self.get_or_create(session_id)

        if tool_name in self.RESEARCH_EXEMPT_TOOLS:
            return state

        if not state.research_done:
            raise ResearchRequiredError(tool_name)

        if not state.is_fresh:
            raise ResearchRequiredError(
                f"{tool_name} (research expired after 30min — run deep_research again)"
            )

        return state

    def should_research(self, session_id: str, tool_name: str) -> str | None:
        """Return a warning if the agent should re-research before continuing.

        Returns None if no warning is needed, or a markdown string with the warning.
        """
        state = self.get_or_create(session_id)

        if tool_name in self.RESEARCH_EXEMPT_TOOLS:
            return None

        if not state.research_done:
            return None  # check_research will block anyway

        non_research_tools = [t for t in state.tools_called if t not in self.RESEARCH_EXEMPT_TOOLS]

        drift_reasons: list[str] = []
        if state.workspace_snapshot.files:
            drift_reasons = compare_snapshots(state.workspace_snapshot)

        error_drift = bool(
            state.last_error_signature
            and state.research_error_signature != state.last_error_signature
        )

        if drift_reasons or error_drift:
            error_line = ""
            if error_drift:
                error_line = "recent tool error"
            return format_drift_warning(
                drift_reasons,
                suggest_research_queries(drift_reasons, state.research_query, error_line),
                error_drift=error_drift,
            )

        if len(non_research_tools) >= self.MAX_TOOLS_WITHOUT_RESEARCH:
            return (
                f"\n\n🟡 **Mid-task warning**: You have called {len(non_research_tools)} tools "
                f"since your last research. Consider re-running `deep_research()` to refresh "
                f"your knowledge before continuing."
            )

        if state.research_age_seconds > 900 and len(non_research_tools) >= 2:
            return (
                "\n\n🟡 **Research aging**: Last research was "
                f"{int(state.research_age_seconds // 60)}+ minutes ago. "
                "Consider `deep_research()` if you changed direction or dependencies."
            )

        return None

    def drift_summary(self, session_id: str) -> dict[str, Any]:
        """Read-only drift report for drift_status tool."""
        state = self.get_or_create(session_id)
        current = snapshot_workspace()
        reasons = (
            compare_snapshots(state.workspace_snapshot) if state.workspace_snapshot.files else []
        )
        return {
            "research_done": state.research_done,
            "research_id": state.research_id,
            "research_query": state.research_query,
            "research_age_seconds": state.research_age_seconds,
            "workspace_root": current.root,
            "manifest_files_tracked": list(current.files.keys()),
            "drift_detected": bool(reasons)
            or (
                state.last_error_signature
                and state.research_error_signature != state.last_error_signature
            ),
            "manifest_changes": reasons,
            "error_signature_changed": bool(
                state.last_error_signature
                and state.research_error_signature != state.last_error_signature
            ),
            "suggested_queries": suggest_research_queries(reasons, state.research_query),
        }

    async def validate_code_generation(
        self,
        session_id: str,
        research_id: str,
        proposed_code: str,
    ) -> dict[str, Any]:
        """Validate that code generation is backed by actual research.

        1. research_id must match the completed session's research_id.
        2. proposed_code must contain at least one citation [N] from research.
        3. Returns validation report with pass/fail and details.
        """
        state = self.get_or_create(session_id)

        if not state.research_done:
            raise CodeGenerationBlockedError("no research has been performed in this session.")

        if not state.is_fresh:
            raise CodeGenerationBlockedError("research is stale (>30min). Re-run deep_research.")

        if research_id != state.research_id:
            raise CodeGenerationBlockedError(
                f"research_id mismatch. Expected '{state.research_id}', got '{research_id}'. "
                "Use the research_id returned by deep_research()."
            )

        # Check for citations in proposed code
        import re

        code_citations = set(re.findall(r"\[(\d+)\]", proposed_code))
        research_citations = set(state.citations_found)

        missing = code_citations - research_citations
        unmatched = research_citations - code_citations

        validation = {
            "passed": len(code_citations) > 0 and not missing,
            "code_citations": sorted(code_citations),
            "research_citations": sorted(research_citations),
            "missing_citations": sorted(missing),
            "unused_citations": sorted(unmatched),
            "research_query": state.research_query,
            "research_age_seconds": state.research_age_seconds,
            "research_id": state.research_id,
        }
        return validation

    async def session_summary(self, session_id: str) -> dict[str, Any]:
        state = self.get_or_create(session_id)
        return {
            "session_id": state.session_id,
            "research_done": state.research_done,
            "research_query": state.research_query,
            "research_age_seconds": state.research_age_seconds,
            "is_fresh": state.is_fresh,
            "research_id": state.research_id,
            "tools_called": state.tools_called,
            "citations_found": state.citations_found,
            "code_generated": state.code_generated,
        }

    async def prune_stale_sessions(self, max_age_seconds: float = 3600) -> int:
        """Remove sessions older than max_age_seconds. Returns count removed."""
        now = time.time()
        async with self._lock:
            stale = [
                sid for sid, s in self._sessions.items() if now - s.created_at > max_age_seconds
            ]
            for sid in stale:
                del self._sessions[sid]
            return len(stale)


# Global singleton enforcer instance
_enforcer: SessionEnforcer | None = None


def get_enforcer() -> SessionEnforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = SessionEnforcer()
    return _enforcer
