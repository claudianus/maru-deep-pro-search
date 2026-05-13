"""Structured research-coding workflow engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .persistence import KnowledgeEntry, KnowledgeStore

logger = logging.getLogger("maru_deep_pro_search.harness.workflow")


class WorkflowPhase(Enum):
    """Phases of the research-first development cycle."""

    CONTEXT_LOAD = "context_load"
    RESEARCH = "research"
    GAP_DETECTION = "gap_detection"
    DESIGN = "design"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    COMPLETE = "complete"


@dataclass
class PhaseResult:
    """Result of executing a single workflow phase."""

    phase: WorkflowPhase
    success: bool
    output: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""


@dataclass
class WorkflowState:
    """Mutable state carried across phases."""

    query: str
    phase: WorkflowPhase = WorkflowPhase.CONTEXT_LOAD
    history: list[PhaseResult] = field(default_factory=list)
    knowledge_entries: list[KnowledgeEntry] = field(default_factory=list)
    design_doc: str = ""
    implementation: str = ""
    verification_result: str = ""
    citations: list[str] = field(default_factory=list)


class WorkflowEngine:
    """Orchestrates the research-first development loop.

    Usage:
        engine = WorkflowEngine(store=KnowledgeStore(...))
        state = WorkflowState(query="Build a real-time chat with SSE")
        for phase_result in engine.run(state):
            print(phase_result.phase.value, phase_result.success)
    """

    def __init__(self, store: KnowledgeStore | None = None) -> None:
        self.store = store

    def run(self, state: WorkflowState) -> Any:
        """Execute the full workflow, yielding results phase by phase."""
        phases = [
            WorkflowPhase.CONTEXT_LOAD,
            WorkflowPhase.RESEARCH,
            WorkflowPhase.GAP_DETECTION,
            WorkflowPhase.DESIGN,
            WorkflowPhase.IMPLEMENT,
            WorkflowPhase.VERIFY,
            WorkflowPhase.COMPLETE,
        ]

        for phase in phases:
            if self._should_skip(state, phase):
                continue
            result = self._execute_phase(state, phase)
            state.history.append(result)
            state.phase = phase
            yield result
            if not result.success and phase != WorkflowPhase.GAP_DETECTION:
                logger.error("Workflow halted at %s", phase.value)
                break

    # ── phase implementations ───────────────────────────────────

    def _execute_phase(self, state: WorkflowState, phase: WorkflowPhase) -> PhaseResult:
        now = datetime.now(timezone.utc).isoformat()
        result = PhaseResult(phase=phase, success=True, started_at=now)

        try:
            if phase == WorkflowPhase.CONTEXT_LOAD:
                self._phase_context_load(state, result)
            elif phase == WorkflowPhase.RESEARCH:
                self._phase_research(state, result)
            elif phase == WorkflowPhase.GAP_DETECTION:
                self._phase_gap_detection(state, result)
            elif phase == WorkflowPhase.DESIGN:
                self._phase_design(state, result)
            elif phase == WorkflowPhase.IMPLEMENT:
                self._phase_implement(state, result)
            elif phase == WorkflowPhase.VERIFY:
                self._phase_verify(state, result)
            elif phase == WorkflowPhase.COMPLETE:
                self._phase_complete(state, result)
        except Exception as exc:
            result.success = False
            result.errors.append(str(exc))
            logger.exception("Phase %s failed", phase.value)

        result.finished_at = datetime.now(timezone.utc).isoformat()
        return result

    def _should_skip(self, state: WorkflowState, phase: WorkflowPhase) -> bool:
        # Skip research if we already have relevant cached knowledge
        if phase == WorkflowPhase.RESEARCH and len(state.knowledge_entries) >= 1:
            # Check if cached knowledge covers the query
            cached_queries = [e.query for e in state.knowledge_entries]
            if any(state.query.lower() in cq.lower() for cq in cached_queries):
                logger.info("Skipping research — cached knowledge covers query")
                return True
        return False

    # ── individual phases ───────────────────────────────────────

    def _phase_context_load(self, state: WorkflowState, result: PhaseResult) -> None:
        """Load AGENTS.md and check knowledge store for existing entries."""
        from pathlib import Path

        context_parts: list[str] = []

        # Load AGENTS.md if present
        agents_md = Path("AGENTS.md")
        if agents_md.exists():
            context_parts.append(f"[AGENTS.md]\n{agents_md.read_text(encoding='utf-8')[:2000]}")

        # Query knowledge store
        if self.store:
            entries = self.store.query(state.query, max_results=3)
            state.knowledge_entries = entries
            if entries:
                context_parts.append(f"[Cached Knowledge] {len(entries)} entries found")
                for i, e in enumerate(entries, 1):
                    context_parts.append(f"[{i}] {e.query[:80]}...")

        result.output = "\n".join(context_parts) if context_parts else "No project context loaded."
        result.artifacts["context_loaded"] = bool(context_parts)
        result.artifacts["cached_entries"] = len(state.knowledge_entries)

    def _phase_research(self, state: WorkflowState, result: PhaseResult) -> None:
        """Trigger deep_research via MCP tool (orchestrated by the agent)."""
        # This phase emits instructions for the agent — it cannot call MCP tools directly
        # because it runs inside the Python process, not the MCP client.
        result.output = (
            f"🔴 MANDATORY: Call `deep_research('{state.query}')` NOW.\n\n"
            "Instructions for the agent:\n"
            "1. Call deep_research with the exact query above.\n"
            "2. Save the result to the knowledge store via the returned workflow state.\n"
            "3. Return the synthesized answer and source list.\n"
        )
        result.artifacts["required_tool"] = "deep_research"
        result.artifacts["query"] = state.query

    def _phase_gap_detection(self, state: WorkflowState, result: PhaseResult) -> None:
        """Analyze research results for gaps. If gaps found, loop back to research."""
        if not state.knowledge_entries:
            result.success = False
            result.output = "No research results to analyze for gaps."
            return

        # Simple heuristic: if the latest entry answer is very short, likely a gap
        latest = state.knowledge_entries[-1]
        if len(latest.answer) < 200:
            result.output = (
                f"⚠️ Research result is short ({len(latest.answer)} chars). "
                "Consider a follow-up deep_research with a refined query."
            )
            result.artifacts["gap_detected"] = True
            result.artifacts["suggested_followup"] = f"{state.query} best practices examples"
        else:
            result.output = "✅ Research coverage appears adequate."
            result.artifacts["gap_detected"] = False

    def _phase_design(self, state: WorkflowState, result: PhaseResult) -> None:
        """Produce an architecture/design document based on research."""
        if not state.knowledge_entries:
            result.success = False
            result.errors.append("Cannot design without research results.")
            return

        combined = "\n\n".join(
            f"Source [{i + 1}]: {e.query}\n{e.answer[:800]}"
            for i, e in enumerate(state.knowledge_entries)
        )
        result.output = (
            f"## Design Document for: {state.query}\n\n"
            f"### Research Summary\n{combined}\n\n"
            "### Architecture Decisions\n"
            "(To be filled by the agent based on research above)\n"
        )
        result.artifacts["design_template"] = result.output

    def _phase_implement(self, state: WorkflowState, result: PhaseResult) -> None:
        """Emit implementation instructions with citation requirements."""
        citations = "\n".join(
            f"[{i + 1}] {e.query} — {e.sources[0].get('url', 'N/A') if e.sources else 'N/A'}"
            for i, e in enumerate(state.knowledge_entries)
        )
        result.output = (
            f"## Implementation for: {state.query}\n\n"
            "Write code based on the verified research above.\n\n"
            "### Required Citations\n"
            f"{citations}\n\n"
            "### Rules\n"
            "- Cite sources with [1], [2] in comments.\n"
            "- Verify API signatures match research.\n"
            "- No code without a research citation.\n"
        )
        result.artifacts["citations"] = citations

    def _phase_verify(self, state: WorkflowState, result: PhaseResult) -> None:
        """Verify implementation against research."""
        result.output = (
            "## Verification Checklist\n"
            "- [ ] Code references correct API versions from research.\n"
            "- [ ] All [1], [2] citations match actual sources.\n"
            "- [ ] No deprecated patterns used.\n"
            "- [ ] Security considerations from research applied.\n"
            "- [ ] Run tests and confirm pass.\n"
        )
        result.artifacts["verification_template"] = result.output

    def _phase_complete(self, state: WorkflowState, result: PhaseResult) -> None:
        """Persist final results and close the workflow loop."""
        if self.store and state.knowledge_entries:
            # Save the final synthesized workflow as a knowledge entry
            summary = "\n".join(f"## {r.phase.value}\n{r.output[:500]}" for r in state.history)
            self.store.save(
                query=f"[workflow] {state.query}",
                answer=summary,
                sources=[],
            )
            result.output = f"✅ Workflow complete. {len(state.history)} phases executed."
            result.artifacts["phases_executed"] = len(state.history)
        else:
            result.output = "Workflow complete (no persistence)."
