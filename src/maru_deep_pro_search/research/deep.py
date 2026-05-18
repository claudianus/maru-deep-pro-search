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
from .signals import source_signals

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
    query_coverage: float = 0.0
    access_risk: str = "open"
    access_reasons: list[str] = field(default_factory=list)
    noise_penalty: float = 0.0
    missing_entities: list[str] = field(default_factory=list)


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
        subqueries = expand_query(query, max_subqueries=DEFAULT_CONFIG.deep_max_subqueries)

    # Phase 2: Multi-engine search
    engine_results: dict[str, list[SearchResult]] = {e: [] for e in engines}

    async def _search_one(
        eng_name: str, sq: str, allow_fallback: bool = True
    ) -> tuple[str, str, list[SearchResult]]:
        async with _search_semaphore:
            try:
                search_engine = SearchEngineRegistry.create(eng_name)
                # Locale harness: English tech terms → localized tokens for Naver/Baidu.
                sent = optimize_for_engine(sq, eng_name) if eng_name in ("naver", "baidu") else sq
                serp_cap = min(max_sources * 2, DEFAULT_CONFIG.serp_per_engine_cap)
                results = await asyncio.wait_for(
                    search_engine.search(sent, max_results=serp_cap),
                    timeout=DEFAULT_CONFIG.deep_serp_run_timeout_seconds,
                )
                return (eng_name, sq, results)
            except asyncio.TimeoutError:
                logger.warning(
                    "Search '%s' on %s timed out after %.0fs",
                    sq[:40],
                    eng_name,
                    DEFAULT_CONFIG.deep_serp_run_timeout_seconds,
                )
                return (eng_name, sq, [])
            except NetworkError as exc:
                logger.warning("Search '%s' on %s failed: %s", sq[:40], eng_name, exc)
                fallback = getattr(exc, "suggested_engine", None)
                if fallback and fallback != eng_name and allow_fallback:
                    logger.info("Engine fallback: %s -> %s", eng_name, fallback)
                    return await _search_one(fallback, sq, allow_fallback=False)
                return (eng_name, sq, [])
            except Exception as exc:
                logger.warning("Search '%s' on %s failed: %s", sq[:40], eng_name, exc)
                return (eng_name, sq, [])

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

    search_runs: list[tuple[str, list[SearchResult]]] = []
    all_results = await asyncio.gather(*search_tasks, return_exceptions=True)
    for res in all_results:
        if isinstance(res, tuple):
            eng_name, sq, results = res
            engine_results.setdefault(eng_name, []).extend(results)
            search_runs.append((f"{eng_name}:{len(search_runs) + 1}:{sq[:48]}", results))
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
    ranked = merge_results(engine_results, query, search_runs=search_runs)

    # Phase 3b: Primary source filtering
    if primary_sources_only:
        original_count = len(ranked)
        ranked = [rr for rr in ranked if rr.result.is_primary]
        logger.info("Primary source filter: %d -> %d", original_count, len(ranked))
        if not ranked:
            ranked = [
                rr
                for rr in merge_results(engine_results, query, search_runs=search_runs)
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

        signals = source_signals(query, sr.title, sr.snippet, sr.url)
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
                query_coverage=signals.query_coverage,
                access_risk=signals.access_risk,
                access_reasons=signals.access_reasons,
                noise_penalty=signals.noise_penalty,
                missing_entities=signals.missing_entities,
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

    trace_block = _format_research_trace(result, planned_reads)
    if trace_block:
        lines.append(trace_block)

    insight_block = _format_insight_cards(result.sources)
    if insight_block:
        lines.append(insight_block)

    # Key findings from snippets
    lines.append("### Key Findings")
    lines.append("")
    for src in result.sources[:5]:
        snippet = (src.snippet or "")[:180]
        if snippet:
            lines.append(f"- [{src.citation_id}] {snippet}")
    lines.append("")

    cluster_block = _format_evidence_clusters(result.sources)
    if cluster_block:
        lines.append(cluster_block)

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
        coverage = f" | coverage: {src.query_coverage:.0%}"
        access = "" if src.access_risk == "open" else f" | access: {src.access_risk}"
        noise = f" | noise: -{src.noise_penalty:.1f}" if src.noise_penalty >= 0.5 else ""
        missing = ""
        if src.missing_entities:
            missing = f" | missing: {', '.join(src.missing_entities[:3])}"
        snippet_cap = 400 if i < 8 else 150

        lines.append(f"#### [{src.citation_id}] {src.title}{badge}")
        lines.append(f"{src.url}")
        lines.append(
            f"_score: {src.relevance_score:.1f}{auth}{cross}{primary}{stype}"
            f"{coverage}{access}{noise}{missing}_"
        )
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

    blueprint = _format_answer_blueprint(result)
    if blueprint:
        lines.append(blueprint)

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


def _format_research_trace(result: ResearchResult, planned_reads: list | None = None) -> str:
    """Expose visible deep-research process steps for host UIs and agents."""
    if not result.sources:
        return ""

    source_types = len({src.source_type for src in result.sources if src.source_type})
    primary_count = sum(1 for src in result.sources if src.is_primary)
    open_count = sum(1 for src in result.sources if src.access_risk == "open")
    followup_count = len(result.suggested_followups)
    planned_count = len(planned_reads or [])
    steps = [
        f"Query intent normalized and expanded into {len(result.subqueries)} orthogonal searches",
        f"{result.total_sources} deduplicated sources analyzed across {len(result.search_coverage)} engines",
        f"{primary_count} primary/official sources and {source_types} source categories identified",
        "BM25/RRF/entity coverage/access-risk ranking applied",
        "Version/year/conflict hints checked from top snippets",
        f"{planned_count} best reads selected for fetch_page/fetch_bulk verification",
        f"{followup_count} follow-up gaps generated for iterative research",
    ]

    lines = [
        "### Research Trace",
        "",
        f"_deep research: {result.total_sources} sources analyzed | {len(steps)} steps complete | {open_count} open-access candidates_",
        "",
    ]
    for i, step in enumerate(steps, start=1):
        lines.append(f"{i}. {step}")
    lines.append("")
    return "\n".join(lines)


def _format_insight_cards(sources: list[CitedSource], max_cards: int = 5) -> str:
    """Generate concise UI-style insight cards from high-signal snippets."""
    candidates = [
        src
        for src in sources
        if src.snippet and src.access_risk != "blocked_likely" and src.query_coverage >= 0.2
    ]
    if not candidates:
        return ""

    candidates.sort(
        key=lambda src: (
            src.is_primary,
            src.authority_boost,
            src.query_coverage,
            src.relevance_score,
        ),
        reverse=True,
    )

    seen: set[str] = set()
    cards: list[CitedSource] = []
    for src in candidates:
        normalized = re.sub(r"\W+", " ", src.snippet.lower())[:90]
        if normalized in seen:
            continue
        seen.add(normalized)
        cards.append(src)
        if len(cards) >= max_cards:
            break

    if not cards:
        return ""

    lines = ["### Insights", ""]
    for src in cards:
        snippet = re.sub(r"\s+", " ", src.snippet).strip()
        if len(snippet) > 240:
            snippet = snippet[:237].rstrip() + "..."
        kind = src.source_type.replace("_", " ") if src.source_type != "unknown" else "source"
        lines.append(f"- [{src.citation_id}] **{src.title[:90]}** ({kind}) — {snippet}")
    lines.append("")
    return "\n".join(lines)


def _format_evidence_clusters(sources: list[CitedSource]) -> str:
    """Summarize top-source agreement signals without LLM synthesis."""
    if not sources:
        return ""

    by_type: dict[str, list[CitedSource]] = {}
    for src in sources[:10]:
        by_type.setdefault(src.source_type or "unknown", []).append(src)

    lines = ["### Evidence Clusters", ""]
    for source_type, group in sorted(
        by_type.items(),
        key=lambda item: max(s.relevance_score for s in item[1]),
        reverse=True,
    )[:4]:
        ids = ", ".join(f"[{s.citation_id}]" for s in group[:4])
        avg_coverage = sum(s.query_coverage for s in group) / max(len(group), 1)
        label = source_type.replace("_", " ")
        lines.append(f"- {label}: {ids} (avg coverage {avg_coverage:.0%})")

    access_risks = [s for s in sources[:10] if s.access_risk != "open"]
    if access_risks:
        parts = [
            f"[{s.citation_id}] {s.access_risk}"
            for s in sorted(access_risks, key=lambda item: item.citation_id)[:5]
        ]
        lines.append(f"- Access risks: {', '.join(parts)}")

    low_coverage = [s for s in sources[:10] if s.query_coverage < 0.25]
    if low_coverage:
        ids = ", ".join(f"[{s.citation_id}]" for s in low_coverage[:5])
        lines.append(f"- Low-query-coverage candidates to verify before citing: {ids}")

    lines.append("")
    return "\n".join(lines)


def _format_answer_blueprint(result: ResearchResult) -> str:
    """Return a synthesis plan that pushes host answers toward report quality."""
    if not result.sources:
        return ""
    primary_ids = [f"[{s.citation_id}]" for s in result.sources if s.is_primary][:5]
    independent_ids = [
        f"[{s.citation_id}]"
        for s in result.sources
        if not s.is_primary and s.access_risk == "open" and s.query_coverage >= 0.2
    ][:5]
    risk_ids = [f"[{s.citation_id}]" for s in result.sources if s.access_risk != "open"][:5]

    lines = [
        "### Answer Blueprint",
        "",
        "- Start with a direct recommendation/answer in the first paragraph.",
        "- Then group evidence by model/product/source family instead of listing search results.",
        "- Include a comparison table when candidates, versions, models, or trade-offs appear.",
        "- Use primary sources for factual claims and independent sources only for corroboration.",
    ]
    if primary_ids:
        lines.append(f"- Primary anchors to cite first: {', '.join(primary_ids)}")
    if independent_ids:
        lines.append(f"- Independent corroboration candidates: {', '.join(independent_ids)}")
    if risk_ids:
        lines.append(f"- Mention access/freshness caveats before relying on: {', '.join(risk_ids)}")
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
    avg_coverage = sum(s.query_coverage for s in result.sources) / total
    access_risk_count = sum(1 for s in result.sources if s.access_risk != "open")

    # Coverage: how many engines contributed
    engine_count = len(result.search_coverage)
    engine_score = min(engine_count * 12, 25)

    # Authority ratio
    authority_score = int((authority_count / total) * 20)

    # Primary source ratio
    primary_score = int((primary_count / total) * 15)

    # High-quality ratio
    quality_score = int((high_quality_count / total) * 10)

    # Cross-engine confirmation ratio
    diversity_score = int((multi_engine_count / total) * 10)
    relevance_score = int(avg_coverage * 20)
    access_penalty = int((access_risk_count / total) * 8)

    return min(
        max(
            engine_score
            + authority_score
            + primary_score
            + quality_score
            + diversity_score
            + relevance_score
            - access_penalty,
            0,
        ),
        100,
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
