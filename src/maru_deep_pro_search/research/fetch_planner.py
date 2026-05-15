"""Heuristic read planner — recommends URLs for the host LLM to fetch.

No local LLM: scoring uses search metadata only (relevance, authority,
source type, query intent). Intelligence stays with the MCP host.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .deep import CitedSource

_INTENT_SECURITY = re.compile(
    r"\b(cve|vulnerability|vulnerabilities|exploit|security|ghsa|advisory|"
    r"patch|zero-?day|malware|rce|xss|csrf)\b",
    re.I,
)
_INTENT_DOCS = re.compile(
    r"\b(api|docs?|documentation|reference|how\s+to|tutorial|guide|"
    r"install|setup|configure|migration|changelog)\b",
    re.I,
)
_INTENT_COMPARE = re.compile(r"\b(vs\.?|versus|compare|comparison|better)\b", re.I)

_TYPE_BOOST: dict[str, dict[str, float]] = {
    "security": {
        "official-docs": 3.0,
        "github-repo": 2.5,
        "package-registry": 2.0,
        "forum": 1.0,
        "blog-review": 0.5,
    },
    "docs": {
        "official-docs": 4.0,
        "package-registry": 3.0,
        "github-repo": 2.0,
        "tutorial": 2.5,
        "blog-review": 0.8,
    },
    "compare": {
        "official-docs": 2.5,
        "github-repo": 2.0,
        "blog-review": 1.5,
        "forum": 1.2,
    },
    "general": {
        "official-docs": 2.5,
        "github-repo": 2.0,
        "academic-paper": 2.0,
        "package-registry": 2.0,
    },
}


@dataclass(frozen=True)
class PlannedRead:
    """A single URL the host should fetch via fetch_page / fetch_bulk."""

    citation_id: int
    url: str
    title: str
    reason: str
    score: float


def detect_query_intent(query: str) -> str:
    """Classify query intent without ML (regex only)."""
    if _INTENT_SECURITY.search(query):
        return "security"
    if _INTENT_COMPARE.search(query):
        return "compare"
    if _INTENT_DOCS.search(query):
        return "docs"
    return "general"


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _score_source(src: CitedSource, intent: str) -> float:
    boosts = _TYPE_BOOST.get(intent, _TYPE_BOOST["general"])
    score = src.relevance_score
    score += boosts.get(src.source_type, 1.0)
    if src.is_primary:
        score += 2.0
    if src.authority_boost:
        score += 1.5
    if src.quality == "high":
        score += 1.0
    if len(src.engines_found) > 1:
        score += 0.8
    if intent == "security" and any(
        x in src.url.lower() for x in ("nvd.nist", "github.com/advisories", "security")
    ):
        score += 2.0
    return score


def _reason_for(src: CitedSource, intent: str) -> str:
    parts: list[str] = []
    if src.is_primary:
        parts.append("primary source")
    if src.authority_boost:
        parts.append("authority domain")
    if len(src.engines_found) > 1:
        parts.append(f"confirmed by {len(src.engines_found)} engines")
    if src.source_type not in ("unknown", ""):
        parts.append(src.source_type.replace("-", " "))
    if intent == "security" and "security" in src.url.lower():
        parts.append("security-related URL")
    if not parts:
        parts.append(f"top relevance ({src.relevance_score:.1f})")
    return "; ".join(parts[:3])


def plan_reads(
    query: str,
    sources: list[CitedSource],
    max_reads: int = 3,
) -> list[PlannedRead]:
    """Pick up to *max_reads* URLs for the host LLM to fetch (metadata-only)."""
    if not sources or max_reads <= 0:
        return []

    intent = detect_query_intent(query)
    ranked = sorted(sources, key=lambda s: _score_source(s, intent), reverse=True)

    chosen: list[PlannedRead] = []
    seen_domains: set[str] = set()

    for src in ranked:
        if len(chosen) >= max_reads:
            break
        dom = _domain(src.url)
        if intent == "compare" and dom and dom in seen_domains:
            continue
        if dom:
            seen_domains.add(dom)
        chosen.append(
            PlannedRead(
                citation_id=src.citation_id,
                url=src.url,
                title=src.title,
                reason=_reason_for(src, intent),
                score=round(_score_source(src, intent), 2),
            )
        )

    # Fill remaining slots if compare mode skipped too many
    if len(chosen) < max_reads:
        picked_ids = {p.citation_id for p in chosen}
        for src in ranked:
            if len(chosen) >= max_reads:
                break
            if src.citation_id in picked_ids:
                continue
            chosen.append(
                PlannedRead(
                    citation_id=src.citation_id,
                    url=src.url,
                    title=src.title,
                    reason=_reason_for(src, intent),
                    score=round(_score_source(src, intent), 2),
                )
            )
    return chosen


def format_planned_reads(planned: list[PlannedRead]) -> str:
    """Markdown block for deep_research output (host consumes, no synthesis)."""
    if not planned:
        return ""

    lines = [
        "### Recommended Reads",
        "",
        "_Host: call `fetch_page` or `fetch_bulk` on these IDs first (metadata-ranked, no local LLM)._",
        "",
    ]
    for p in planned:
        lines.append(f"- **[{p.citation_id}]** {p.title}")
        lines.append(f"  - URL: {p.url}")
        lines.append(f"  - Why: {p.reason}")
    lines.append("")
    return "\n".join(lines)
