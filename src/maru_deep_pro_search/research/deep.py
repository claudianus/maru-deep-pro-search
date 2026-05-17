"""Deep search pipeline — multi-engine search with intelligent ranking.

Returns ranked URL lists with rich metadata (title, snippet, authority,
cross-engine confirmation). Content fetching and answer synthesis are
delegated to the agent's LLM, which uses fetch_page / fetch_bulk tools.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

from ..config import DEFAULT_CONFIG
from ..engines.base import SearchResult
from ..engines.registry import SearchEngineRegistry
from ..exceptions import NetworkError
from ..utils.locale_harness import optimize_for_engine
from ..utils.url import is_authority_domain
from .expander import expand_query
from .gap_detector import detect_gaps
from .ranker import merge_results

logger = logging.getLogger(__name__)

# ── Data models ───────────────────────────────────────────────────────────


@dataclass
class CitedSource:
    """A source with citation ID and search metadata."""

    citation_id: int
    url: str
    title: str
    snippet: str = ""
    quality: str = ""
    source_type: str = "unknown"
    is_primary: bool = False
    authority_boost: bool = False
    engines_found: list[str] = field(default_factory=list)
    relevance_score: float = 0.0


@dataclass
class ResearchResult:
    """Research result with ranked sources and metadata."""

    query: str
    engine: str
    total_sources: int
    sources: list[CitedSource] = field(default_factory=list)
    elapsed_ms: float = 0.0
    subqueries: list[str] = field(default_factory=list)
    suggested_followups: list[str] = field(default_factory=list)
    search_coverage: dict[str, int] = field(default_factory=dict)


# ── Main pipeline ─────────────────────────────────────────────────────────

# Module-level semaphore to limit concurrent search requests across all calls
_search_semaphore = asyncio.Semaphore(4)


async def deep_research(
    query: str,
    engine: str = DEFAULT_CONFIG.default_engine,
    max_sources: int = DEFAULT_CONFIG.deep_max_sources,
    expand_queries: bool = True,
    primary_sources_only: bool = False,
) -> ResearchResult:
    """Deep multi-engine search with query expansion and intelligent ranking.

    Returns a ranked list of URLs with rich metadata. The agent's LLM
    decides which sources to fetch using fetch_page / fetch_bulk tools.

    Args:
        query: Search query.
        engine: Search engine variant (default: duckduckgo_lite).
        max_sources: Max unique sources to return.
        expand_queries: Generate subqueries for broader coverage.
        primary_sources_only: Filter to official docs, GitHub, registries,
            academic papers, and Stack Overflow only.
    """
    t0 = time.monotonic()

    # Phase 0: Engine selection
    if not SearchEngineRegistry.is_registered(engine):
        logger.warning(
            "Engine '%s' not registered, falling back to %s",
            engine,
            DEFAULT_CONFIG.default_engine,
        )
        engine = DEFAULT_CONFIG.default_engine
    if not SearchEngineRegistry.is_registered(engine):
        engine = "duckduckgo_lite"

    if engine == "duckduckgo_lite":
        raw_engines = SearchEngineRegistry.recommend_engines(query, count=6)
        seen_classes: set[type] = set()
        engines: list[str] = []
        for e in raw_engines:
            try:
                eng_cls = SearchEngineRegistry.get(e)
                if eng_cls not in seen_classes:
                    seen_classes.add(eng_cls)
                    engines.append(e)
            except ValueError:
                continue
        engines = engines[:3]
        logger.info("Auto-selected engines: %s", engines)
    else:
        engines = [engine]

    if not engines:
        engines = ["duckduckgo_lite"]

    # Phase 1: Query expansion
    subqueries = [query]
    if expand_queries:
        subqueries = expand_query(query, max_subqueries=5)

    # Phase 2: Multi-engine search
    engine_results: dict[str, list[SearchResult]] = {e: [] for e in engines}

    async def _search_one(
        eng_name: str, sq: str, allow_fallback: bool = True
    ) -> tuple[str, list[SearchResult]]:
        async with _search_semaphore:
            try:
                search_engine = SearchEngineRegistry.create(eng_name)
                # Locale harness: English tech terms → localized tokens for Naver/Baidu.
                sent = optimize_for_engine(sq, eng_name) if eng_name in ("naver", "baidu") else sq
                serp_cap = min(max_sources * 2, DEFAULT_CONFIG.serp_per_engine_cap)
                results = await search_engine.search(sent, max_results=serp_cap)
                return (eng_name, results)
            except NetworkError as exc:
                logger.warning("Search '%s' on %s failed: %s", sq[:40], eng_name, exc)
                fallback = getattr(exc, "suggested_engine", None)
                if fallback and fallback != eng_name and allow_fallback:
                    logger.info("Engine fallback: %s -> %s", eng_name, fallback)
                    return await _search_one(fallback, sq, allow_fallback=False)
                return (eng_name, [])
            except Exception as exc:
                logger.warning("Search '%s' on %s failed: %s", sq[:40], eng_name, exc)
                return (eng_name, [])

    # Pre-filter engines with open circuit breakers
    available_engines: list[str] = []
    for eng_name in engines:
        try:
            search_engine = SearchEngineRegistry.create(eng_name)
            if await search_engine._check_circuit():
                available_engines.append(eng_name)
            else:
                logger.info("Skipping %s (circuit breaker open)", eng_name)
        except Exception:
            available_engines.append(eng_name)
    if not available_engines:
        available_engines = engines[:1]
    engines = available_engines

    search_tasks: list[asyncio.Task] = []
    for eng_name in engines:
        search_tasks.append(asyncio.create_task(_search_one(eng_name, query)))
    for i, sq in enumerate(subqueries[1:]):
        sub_eng = engines[i % len(engines)]
        search_tasks.append(asyncio.create_task(_search_one(sub_eng, sq)))

    all_results = await asyncio.gather(*search_tasks, return_exceptions=True)
    for res in all_results:
        if isinstance(res, tuple):
            eng_name, results = res
            engine_results[eng_name].extend(results)
        elif isinstance(res, Exception):
            logger.warning("Search task failed: %s", res)

    all_results_flat = [r for results in engine_results.values() for r in results]
    if not all_results_flat:
        return ResearchResult(
            query=query,
            engine=engines[0],
            total_sources=0,
            subqueries=subqueries,
        )

    # Phase 3: Merge, deduplicate, and rank
    ranked = merge_results(engine_results, query)

    # Phase 3b: Primary source filtering
    if primary_sources_only:
        original_count = len(ranked)
        ranked = [rr for rr in ranked if rr.result.is_primary]
        logger.info("Primary source filter: %d -> %d", original_count, len(ranked))
        if not ranked:
            ranked = [
                rr
                for rr in merge_results(engine_results, query)
                if rr.result.url_suggests_docs or is_authority_domain(rr.result.url)
            ]

    # Phase 4: Build CitedSource from search metadata (no fetching)
    sources: list[CitedSource] = []
    seen_urls: set[str] = set()
    search_coverage: dict[str, int] = {}

    for rr in ranked[:max_sources]:
        sr = rr.result
        if sr.url in seen_urls:
            continue
        seen_urls.add(sr.url)

        for engine_name in sr.engines_found:
            search_coverage[engine_name] = search_coverage.get(engine_name, 0) + 1

        sources.append(
            CitedSource(
                citation_id=len(sources) + 1,
                url=sr.url,
                title=sr.title,
                snippet=sr.snippet,
                quality=_estimate_quality(sr),
                source_type=sr.source_type.value if sr.source_type else "unknown",
                is_primary=sr.is_primary,
                authority_boost=is_authority_domain(sr.url),
                engines_found=sr.engines_found,
                relevance_score=round(rr.final_score, 2),
            )
        )

    # Phase 5: Gap detection
    suggested_followups = detect_gaps(query, sources)

    elapsed = (time.monotonic() - t0) * 1000

    return ResearchResult(
        query=query,
        engine=engines[0],
        total_sources=len(sources),
        sources=sources,
        elapsed_ms=elapsed,
        subqueries=subqueries,
        suggested_followups=suggested_followups,
        search_coverage=search_coverage,
    )


# ── Output formatting ─────────────────────────────────────────────────────


def format_for_llm(
    result: ResearchResult,
    planned_reads: list | None = None,
) -> str:
    """Format research results into markdown for agent consumption.

    Returns ranked URLs with metadata badges. The agent decides which
    sources to fetch using fetch_page / fetch_bulk tools.
    """
    from .fetch_planner import format_planned_reads, plan_reads

    if planned_reads is None:
        planned_reads = plan_reads(result.query, result.sources)
    if not result.sources:
        return f"No results found for: '{result.query}'"

    lines: list[str] = []
    lines.append(f"## Research: {result.query}")

    coverage_str = " ".join(f"{k}={v}" for k, v in result.search_coverage.items())

    grade_emoji, grade, quality_score = _research_quality_display(result)

    lines.append(
        f"_engines: {coverage_str} | sources: {result.total_sources} | "
        f"{result.elapsed_ms:.0f}ms | quality: {grade_emoji} {grade} ({quality_score}/100)_"
    )

    if len(result.subqueries) > 1:
        lines.append(f"_subqueries: {', '.join(result.subqueries)}_")
    lines.append("")

    # Key findings from snippets
    lines.append("### Key Findings")
    lines.append("")
    for src in result.sources[:5]:
        snippet = (src.snippet or "")[:180]
        if snippet:
            lines.append(f"- [{src.citation_id}] {snippet}")
    lines.append("")

    planned_block = format_planned_reads(planned_reads)
    if planned_block:
        lines.append(planned_block)

    # Sources with rich metadata
    lines.append("### Sources")
    lines.append("")

    for i, src in enumerate(result.sources):
        badge = " **[HIGH]**" if src.quality == "high" else ""
        auth = " | 🔒 authority" if src.authority_boost else ""
        cross = f" | ✓{len(src.engines_found)} engines" if len(src.engines_found) > 1 else ""
        primary = " | 📌 primary" if src.is_primary else ""
        stype = f" | {src.source_type}" if src.source_type != "unknown" else ""
        snippet_cap = 400 if i < 8 else 150

        lines.append(f"#### [{src.citation_id}] {src.title}{badge}")
        lines.append(f"{src.url}")
        lines.append(f"_score: {src.relevance_score:.1f}{auth}{cross}{primary}{stype}_")
        if src.snippet:
            lines.append(f"\n> {src.snippet[:snippet_cap]}\n")
        else:
            lines.append("")

    conflict_block = _format_snippet_conflicts(result.sources)
    if conflict_block:
        lines.append(conflict_block)

    # Suggested follow-ups
    if result.suggested_followups:
        lines.append("### Suggested Follow-up Research")
        lines.append("")
        for sq in result.suggested_followups:
            lines.append(f"- {sq}")
        lines.append("")

    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────


def _format_snippet_conflicts(sources: list) -> str:
    """Surface contradictory version/year hints across top snippets."""
    version_hits: dict[str, set[int]] = {}
    year_hits: dict[str, set[int]] = {}
    for src in sources[:10]:
        text = src.snippet or ""
        for ver in dict.fromkeys(re.findall(r"\bv?\d+\.\d+(?:\.\d+)?\b", text)):
            version_hits.setdefault(ver, set()).add(src.citation_id)
        for year in dict.fromkeys(re.findall(r"20\d{2}", text)):
            year_hits.setdefault(year, set()).add(src.citation_id)
    conflicts: list[str] = []
    if len(version_hits) > 1 and len({cid for ids in version_hits.values() for cid in ids}) > 1:
        parts = [
            f"{v} [{', '.join(f'#{i}' for i in sorted(ids))}]" for v, ids in version_hits.items()
        ]
        conflicts.append("- Version hints differ: " + "; ".join(parts[:4]))
    if len(year_hits) > 1 and len({cid for ids in year_hits.values() for cid in ids}) > 1:
        parts = [f"{y} [{', '.join(f'#{i}' for i in sorted(ids))}]" for y, ids in year_hits.items()]
        conflicts.append("- Year hints differ: " + "; ".join(parts[:4]))
    if not conflicts:
        return ""
    lines = ["### Conflicts", "", "_Verify before citing:_", ""]
    lines.extend(conflicts)
    lines.append("")
    return "\n".join(lines)


def _compute_research_quality(result: ResearchResult) -> int:
    """Score research quality 0-100 based on source diversity, authority, and coverage."""
    if not result.sources:
        return 0

    total = len(result.sources)
    authority_count = sum(1 for s in result.sources if s.authority_boost)
    primary_count = sum(1 for s in result.sources if s.is_primary)
    high_quality_count = sum(1 for s in result.sources if s.quality == "high")
    multi_engine_count = sum(1 for s in result.sources if len(s.engines_found) > 1)

    # Coverage: how many engines contributed
    engine_count = len(result.search_coverage)
    coverage_score = min(engine_count * 15, 30)  # 2 engines=30, 1 engine=15

    # Authority ratio
    authority_score = int((authority_count / total) * 25)

    # Primary source ratio
    primary_score = int((primary_count / total) * 20)

    # High-quality ratio
    quality_score = int((high_quality_count / total) * 15)

    # Cross-engine confirmation ratio
    diversity_score = int((multi_engine_count / total) * 10)

    return min(
        coverage_score + authority_score + primary_score + quality_score + diversity_score, 100
    )


def _research_quality_display(result: ResearchResult) -> tuple[str, str, int]:
    """Shared emoji, letter grade, and numeric score for quality lines."""
    score = _compute_research_quality(result)
    grade = _quality_grade(score)
    grade_emoji = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"}.get(grade, "⚪")
    return grade_emoji, grade, score


def research_quality_line(result: ResearchResult) -> str:
    """One-line quality summary for answer-engine and tool headers."""
    grade_emoji, grade, score = _research_quality_display(result)
    return f"quality: {grade_emoji} {grade} ({score}/100)"


def _quality_grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _estimate_quality(result: SearchResult) -> str:
    """Estimate source quality from search metadata (no fetch required)."""
    score = 0
    if is_authority_domain(result.url):
        score += 2
    if result.is_primary:
        score += 1
    if result.url_suggests_docs:
        score += 1
    if len(result.engines_found) > 1:
        score += 1

    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"
