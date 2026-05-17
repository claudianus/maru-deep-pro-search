"""Shared post-search persistence: receipts, knowledge store, research IDs."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .deep import ResearchResult, format_for_llm, research_quality_line
from .fetch_planner import PlannedRead, plan_reads
from .receipt import generate_research_id, write_receipt

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PersistedResearch:
    """Artifacts written after a successful research run."""

    research_id: str
    planned: list[PlannedRead]
    receipt_path: Path | None
    formatted_packet: str


def persist_research_artifacts(
    *,
    result: ResearchResult,
    formatted_packet: str | None = None,
    research_id: str | None = None,
    write_receipt_file: bool = True,
    save_knowledge: bool = True,
    knowledge_answer: str | None = None,
) -> PersistedResearch:
    """Write receipt + knowledge store entry for a research result."""
    rid = research_id or generate_research_id()
    planned = plan_reads(result.query, result.sources)
    packet = (
        formatted_packet
        if formatted_packet is not None
        else format_for_llm(result, planned_reads=planned)
    )

    receipt_path: Path | None = None
    if write_receipt_file:
        try:
            receipt_path = write_receipt(rid, result, packet, planned)
        except OSError as exc:
            logger.debug("Receipt write failed (non-critical): %s", exc)

    if save_knowledge:
        try:
            from ..harness.persistence import KnowledgeStore

            sources: list[dict[str, Any]] = [
                {
                    "url": s.url,
                    "title": s.title,
                    "snippet": s.snippet,
                    "quality": s.quality,
                    "engines_found": s.engines_found,
                    "relevance_score": s.relevance_score,
                }
                for s in result.sources
            ]
            answer_body = knowledge_answer if knowledge_answer is not None else packet
            KnowledgeStore().save(query=result.query, answer=answer_body, sources=sources)
        except Exception:
            logger.debug("KnowledgeStore save failed (non-critical)", exc_info=True)

    return PersistedResearch(
        research_id=rid,
        planned=planned,
        receipt_path=receipt_path,
        formatted_packet=packet,
    )


def save_research_knowledge(result: ResearchResult, answer: str) -> None:
    """Persist final tool output (including footers) to KnowledgeStore."""
    try:
        from ..harness.persistence import KnowledgeStore

        sources: list[dict[str, Any]] = [
            {
                "url": s.url,
                "title": s.title,
                "snippet": s.snippet,
                "quality": s.quality,
                "engines_found": s.engines_found,
                "relevance_score": s.relevance_score,
            }
            for s in result.sources
        ]
        KnowledgeStore().save(query=result.query, answer=answer, sources=sources)
    except Exception:
        logger.debug("KnowledgeStore save failed (non-critical)", exc_info=True)


def append_research_footer(text: str, research_id: str, receipt_path: Path | None) -> str:
    """Append standard research_id / receipt footers for MCP output."""
    if re.search(r"_research_id:\s*RSCH-[A-F0-9]+_", text, re.I):
        return text
    footer = f"\n\n_research_id: {research_id}_"
    if receipt_path is not None:
        footer += f"\n_receipt: {receipt_path}_"
    return text + footer


def answer_quality_suffix(result: ResearchResult) -> str:
    """Compact quality line aligned with deep_research output."""
    return research_quality_line(result)
