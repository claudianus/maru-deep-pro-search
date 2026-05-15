"""Research receipts — lightweight audit trail on disk (~few KB each)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .deep import ResearchResult
from .fetch_planner import PlannedRead, plan_reads

logger = logging.getLogger(__name__)

_DEFAULT_MAX_RECEIPTS = 48
_RECEIPT_TTL_DAYS = 14


def generate_research_id() -> str:
    return f"RSCH-{uuid.uuid4().hex[:12].upper()}"


def receipts_dir() -> Path:
    return Path.home() / ".maru" / "receipts"


def write_receipt(
    research_id: str,
    result: ResearchResult,
    formatted_output: str,
    planned: list[PlannedRead] | None = None,
) -> Path:
    """Write markdown + minimal JSON receipt. Returns path to .md file."""
    planned = planned if planned is not None else plan_reads(result.query, result.sources)
    out_dir = receipts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"{research_id}.md"
    json_path = out_dir / f"{research_id}.json"

    now = datetime.now(timezone.utc).isoformat()
    citation_map = {str(s.citation_id): s.url for s in result.sources}

    payload: dict[str, Any] = {
        "research_id": research_id,
        "query": result.query,
        "created_at": now,
        "engines": result.search_coverage,
        "source_count": result.total_sources,
        "elapsed_ms": round(result.elapsed_ms, 1),
        "citations": citation_map,
        "planned_reads": [
            {
                "id": p.citation_id,
                "url": p.url,
                "title": p.title,
                "reason": p.reason,
            }
            for p in planned
        ],
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Research Receipt `{research_id}`",
        "",
        f"- **Query**: {result.query}",
        f"- **Created**: {now}",
        f"- **Sources**: {result.total_sources} | **Elapsed**: {result.elapsed_ms:.0f}ms",
        f"- **Engines**: {', '.join(f'{k}={v}' for k, v in result.search_coverage.items())}",
        "",
        "## Recommended Reads",
        "",
    ]
    for p in planned:
        lines.append(f"- [{p.citation_id}] {p.title} — {p.reason}")
        lines.append(f"  - {p.url}")
    lines.append("")
    lines.append("## Citations")
    lines.append("")
    for cid, url in sorted(citation_map.items(), key=lambda x: int(x[0])):
        lines.append(f"- [{cid}] {url}")
    lines.append("")
    lines.append("## Agent Output (excerpt)")
    lines.append("")
    excerpt = formatted_output[:4000]
    if len(formatted_output) > 4000:
        excerpt += "\n\n… (truncated)"
    lines.append(excerpt)

    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.debug("Wrote research receipt %s", md_path)
    prune_receipts()
    return md_path


def prune_receipts(
    max_files: int = _DEFAULT_MAX_RECEIPTS, ttl_days: int = _RECEIPT_TTL_DAYS
) -> int:
    """Remove old receipts to cap disk use. Returns count deleted."""
    out_dir = receipts_dir()
    if not out_dir.is_dir():
        return 0

    now = datetime.now(timezone.utc)
    removed = 0
    files = sorted(out_dir.glob("RSCH-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    for path in files[max_files:]:
        try:
            path.unlink(missing_ok=True)
            json_path = path.with_suffix(".json")
            json_path.unlink(missing_ok=True)
            removed += 1
        except OSError:
            pass

    cutoff = ttl_days * 86400
    for path in out_dir.glob("RSCH-*.md"):
        try:
            age = now.timestamp() - path.stat().st_mtime
            if age > cutoff:
                path.unlink(missing_ok=True)
                path.with_suffix(".json").unlink(missing_ok=True)
                removed += 1
        except OSError:
            pass

    return removed
