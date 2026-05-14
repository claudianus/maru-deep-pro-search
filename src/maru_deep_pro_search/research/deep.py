"""Deep search pipeline — multi-engine search with intelligent ranking.

Returns ranked URL lists with rich metadata (title, snippet, authority,
cross-engine confirmation). Content fetching and answer synthesis are
delegated to the agent's LLM, which uses fetch_page / fetch_bulk tools.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from ..engines.base import SearchResult
from ..engines.registry import SearchEngineRegistry
from ..exceptions import NetworkError, ParseError
from ..utils.retry import with_retry
from ..utils.url import is_authority_domain
from .expander import expand_query
from .gap_detector import detect_gaps
from .ranker import merge_results

logger = logging.getLogger(__name__)

_PROBLEMATIC_ENGINES = {"yahoo", "startpage"}


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


async def deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 30,
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
        logger.warning("Engine '%s' not registered, falling back to duckduckgo_lite", engine)
        engine = "duckduckgo_lite"

    if engine == "duckduckgo_lite":
        raw_engines = SearchEngineRegistry.recommend_engines(query, count=6)
        seen_classes: set[type] = set()
        engines: list[str] = []
        for e in raw_engines:
            if e in _PROBLEMATIC_ENGINES:
                continue
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
    _search_semaphore = asyncio.Semaphore(4)

    async def _search_one(
        eng_name: str, sq: str, allow_fallback: bool = True
    ) -> tuple[str, list[SearchResult]]:
        async with _search_semaphore:
            try:
                search_engine = SearchEngineRegistry.create(eng_name)
                results = await with_retry(
                    search_engine.search,
                    sq,
                    max_results=max_sources * 3,
                    max_attempts=2,
                    retryable_exceptions=(NetworkError, ParseError),
                )
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


def format_for_llm(result: ResearchResult) -> str:
    """Format research results into markdown for agent consumption.

    Returns ranked URLs with metadata badges. The agent decides which
    sources to fetch using fetch_page / fetch_bulk tools.
    """
    if not result.sources:
        return f"No results found for: '{result.query}'"

    lines: list[str] = []
    lines.append(f"## Research: {result.query}")

    coverage_str = " ".join(f"{k}={v}" for k, v in result.search_coverage.items())
    lines.append(
        f"_engines: {coverage_str} | sources: {result.total_sources} | {result.elapsed_ms:.0f}ms_"
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

    # Sources with rich metadata
    lines.append("### Sources")
    lines.append("")

    for src in result.sources:
        badge = " **[HIGH]**" if src.quality == "high" else ""
        auth = " | 🔒 authority" if src.authority_boost else ""
        cross = f" | ✓{len(src.engines_found)} engines" if len(src.engines_found) > 1 else ""
        primary = " | 📌 primary" if src.is_primary else ""
        stype = f" | {src.source_type}" if src.source_type != "unknown" else ""

        lines.append(f"#### [{src.citation_id}] {src.title}{badge}")
        lines.append(f"{src.url}")
        lines.append(f"_score: {src.relevance_score:.1f}{auth}{cross}{primary}{stype}_")
        if src.snippet:
            lines.append(f"\n> {src.snippet[:400]}\n")
        else:
            lines.append("")

    # Suggested follow-ups
    if result.suggested_followups:
        lines.append("### Suggested Follow-up Research")
        lines.append("")
        for sq in result.suggested_followups:
            lines.append(f"- {sq}")
        lines.append("")

    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────


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
