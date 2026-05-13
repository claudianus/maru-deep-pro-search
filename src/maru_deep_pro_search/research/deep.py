"""Enhanced deep research pipeline with citations and answer synthesis.

Perplexity-level search: multi-engine crawling, intelligent ranking,
citation-native output, and rule-based answer synthesis."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

from ..engines.base import (
    ExtractionQuality,
    PageContent,
    SearchResult,
    guess_source_type_and_primary,
)
from ..engines.registry import SearchEngineRegistry
from ..exceptions import NetworkError, ParseError
from ..extraction.content import truncate_for_llm
from ..utils.retry import with_retry
from ..utils.url import deduplicate_urls, get_domain, is_authority_domain, should_skip_url
from .expander import expand_query, extract_keywords
from .gap_detector import detect_gaps
from .ranker import _jaccard_similarity, merge_results, rank_pages

logger = logging.getLogger(__name__)


@dataclass
class CitedSource:
    """A source with citation ID for answer synthesis."""

    citation_id: int
    url: str
    title: str
    snippet: str = ""
    content: str = ""
    markdown: str = ""
    content_length: int = 0
    fetch_ms: float = 0.0
    quality: str = ""
    content_type: str = ""
    source_type: str = "unknown"
    is_primary: bool = False
    internal_links: list[dict] = field(default_factory=list)
    external_links: list[dict] = field(default_factory=list)
    code_languages: list[str] = field(default_factory=list)
    api_signatures: list[dict] = field(default_factory=list)
    package_refs: list[dict] = field(default_factory=list)
    code_to_text_ratio: float = 0.0
    published_date: str = ""
    last_updated: str = ""
    crawled_at: str = ""
    freshness_days: int | None = None
    is_api_reference: bool = False
    is_tutorial: bool = False
    is_error_solution: bool = False
    relevance_score: float = 0.0
    authority_boost: bool = False
    engines_found: list[str] = field(default_factory=list)
    github_meta: dict | None = None


@dataclass
class AnswerResult:
    """Synthesized answer with citations."""

    answer: str
    citations: list[CitedSource]
    subqueries: list[str]
    elapsed_ms: float = 0.0


@dataclass
class ResearchResult:
    """Full research result with sources and metadata."""

    query: str
    engine: str
    total_sources: int
    sources: list[CitedSource] = field(default_factory=list)
    elapsed_ms: float = 0.0
    high_quality_count: int = 0
    blocked_count: int = 0
    subqueries: list[str] = field(default_factory=list)
    total_tokens_used: int = 0
    tokens_allocated: int = 0
    sources_summarized: int = 0
    sources_dropped: int = 0
    # Answer synthesis
    synthesized_answer: str = ""
    has_answer: bool = False
    # Follow-up suggestions
    suggested_followups: list[str] = field(default_factory=list)


async def deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 8,
    follow_links: bool = False,
    stealth: bool = False,
    expand_queries: bool = True,
    max_tokens_per_source: int = 2500,
    max_total_tokens: int = 20000,
    summarize: bool = False,
    synthesize_answer: bool = True,
    use_knowledge_store: bool = True,
    primary_sources_only: bool = False,
) -> ResearchResult:
    """End-to-end deep research pipeline with query expansion and multi-pass crawling.

    Args:
        query: Search query.
        engine: Search engine variant (registered in SearchEngineRegistry).
        max_sources: Max unique pages to crawl.
        follow_links: If True, follow one level of external links.
        stealth: Use StealthyFetcher for anti-bot bypass.
        expand_queries: If True, generate subqueries for broader coverage.
        max_tokens_per_source: Token budget per source.
        max_total_tokens: Total output token budget.
        summarize: Enable extractive summarization for over-budget scenarios.
        synthesize_answer: Generate a synthesized answer from sources.
        use_knowledge_store: If True, check local knowledge cache first.
        primary_sources_only: If True, filter out non-primary sources
            (blogs, aggregators) and keep only official docs, GitHub repos,
            package registries, academic papers, and Stack Overflow.
    """
    t0 = time.monotonic()

    store = None
    # Phase 0: Knowledge store cache check
    if use_knowledge_store:
        try:
            from ..harness.persistence import KnowledgeStore
            store = KnowledgeStore()
            cached = store.query(query, max_results=1)
            if cached:
                entry = cached[0]
                logger.info("Knowledge cache HIT for query: %s", query[:60])
                # Reconstruct ResearchResult from cache
                sources = []
                for s in entry.sources:
                    sources.append(CitedSource(
                        citation_id=s.get("citation_id", 1),
                        url=s.get("url", ""),
                        title=s.get("title", ""),
                        snippet=s.get("snippet", ""),
                        content=s.get("content", ""),
                        markdown=s.get("markdown", ""),
                        quality=s.get("quality", ""),
                    ))
                return ResearchResult(
                    query=query,
                    engine="cache",
                    total_sources=len(sources),
                    sources=sources,
                    elapsed_ms=0.0,
                    high_quality_count=sum(1 for s in sources if s.quality == "high"),
                    blocked_count=sum(1 for s in sources if s.quality == "blocked"),
                    subqueries=[query],
                    total_tokens_used=len(entry.answer),
                    tokens_allocated=len(entry.answer),
                    sources_summarized=0,
                    sources_dropped=0,
                    synthesized_answer=entry.answer,
                    has_answer=bool(entry.answer),
                    suggested_followups=[],
                )
        except Exception as exc:
            logger.debug("Knowledge store check failed: %s", exc)

    # Phase 0: Engine selection
    # If default engine, use metadata-based recommendation for multi-engine search
    if not SearchEngineRegistry.is_registered(engine):
        logger.warning("Engine '%s' not registered, falling back to duckduckgo_lite", engine)
        engine = "duckduckgo_lite"

    # Phase 0b: Engine selection — use up to 5 engines for coverage
    if engine == "duckduckgo_lite":
        engines = SearchEngineRegistry.recommend_engines(query, count=5)
        logger.info("Auto-selected engines: %s", engines)
    else:
        engines = [engine]

    primary_engine = SearchEngineRegistry.create(engines[0])

    # Phase 1: Query expansion
    subqueries = [query]
    if expand_queries:
        subqueries = expand_query(query, max_subqueries=5)

    # Phase 2: Search across ALL engines with ALL subqueries
    # Every engine runs every subquery for maximum coverage
    engine_results: dict[str, list[SearchResult]] = {e: [] for e in engines}
    _search_semaphore = asyncio.Semaphore(6)  # Increased for more engines

    async def _search_one(eng_name: str, sq: str) -> tuple[str, list[SearchResult]]:
        async with _search_semaphore:
            try:
                eng = SearchEngineRegistry.create(eng_name)
                results = await with_retry(
                    eng.search,
                    sq,
                    max_results=max_sources * 2,
                    max_attempts=2,
                    retryable_exceptions=(NetworkError, ParseError),
                )
                return (eng_name, results)
            except Exception as exc:
                logger.warning("Subquery '%s' on %s failed: %s", sq[:40], eng_name, exc)
                return (eng_name, [])

    search_tasks: list[asyncio.Task] = []
    for eng_name in engines:
        for sq in subqueries:
            search_tasks.append(asyncio.create_task(_search_one(eng_name, sq)))
    # Also run original query on all engines (in case expander produced poor subqueries)
    for eng_name in engines:
        search_tasks.append(asyncio.create_task(_search_one(eng_name, query)))

    all_results = await asyncio.gather(*search_tasks, return_exceptions=True)
    for res in all_results:
        if isinstance(res, tuple):
            eng_name, results = res
            engine_results[eng_name].extend(results)
        elif isinstance(res, Exception):
            logger.warning("Search task failed: %s", res)

    # Flatten for empty check
    all_results = [r for results in engine_results.values() for r in results]
    if not all_results:
        return ResearchResult(
            query=query,
            engine=engines[0],
            total_sources=0,
            subqueries=subqueries,
        )

    # Phase 3: Deduplicate, score, and rank (multi-engine merge)
    ranked = merge_results(engine_results, query)

    # Phase 3b: Primary source filtering
    if primary_sources_only:
        original_count = len(ranked)
        ranked = [rr for rr in ranked if rr.result.is_primary]
        logger.info(
            "Primary source filter: %d -> %d results",
            original_count, len(ranked),
        )
        if not ranked:
            # Fallback: keep top authority-boosted results
            ranked = [rr for rr in merge_results(engine_results, query)
                      if rr.result.url_suggests_docs or is_authority_domain(rr.result.url)]

    # Phase 4: Crawl top pages (use primary engine for fetching)
    urls_to_fetch = _prioritize_urls([rr.result.url for rr in ranked[:max_sources]])

    # Network health probe + domain history filter
    network = await _probe_network(primary_engine)
    effective_timeout = 5.0
    effective_max_sources = max_sources
    if network["slow"]:
        logger.warning("Slow network (%.0fms). Reducing targets.", network["latency_ms"])
        effective_timeout = 3.0
        effective_max_sources = max(3, max_sources - 2)

    if use_knowledge_store and store:
        urls_to_fetch = _filter_slow_domains(urls_to_fetch, store)
    urls_to_fetch = urls_to_fetch[:effective_max_sources]

    pages = await _fetch_pages(urls_to_fetch, primary_engine, stealth=stealth, timeout_per_fetch=effective_timeout)

    # Record domain performance
    if use_knowledge_store and store:
        for p in pages:
            domain = get_domain(p.url)
            store.record_domain_fetch(domain, p.fetch_duration_ms, p.quality != ExtractionQuality.BLOCKED)

    # Smart fallback: stealth retry for blocked pages
    blocked_stealth = [p for p in pages if p.quality == ExtractionQuality.BLOCKED and p.needs_stealth]
    if blocked_stealth:
        logger.info("Stealth retry for %d blocked pages", len(blocked_stealth))
        stealth_pages = await _fetch_pages(
            [p.url for p in blocked_stealth],
            primary_engine,
            stealth=True,
            max_concurrent=3,
            min_quality_results=1,
            timeout_per_fetch=8.0,
        )
        # Replace blocked entries with stealth results where successful
        stealth_map = {normalize_url(p.url): p for p in stealth_pages if p.quality != ExtractionQuality.BLOCKED}
        pages = [stealth_map.get(normalize_url(p.url), p) for p in pages]

    pages = rank_pages(pages, query)

    # Phase 4b: Recency gate for trends/news queries
    query_type = _classify_query(query)
    if query_type in ("news", "trends"):
        original_count = len(pages)
        filtered_pages = []
        for p in pages:
            freshness_ok = True
            if p.freshness_days is not None and p.freshness_days > 180:
                freshness_ok = False
            elif p.published_date:
                try:
                    dt = datetime.fromisoformat(p.published_date.replace('Z', '+00:00'))
                    age_days = (datetime.now(dt.tzinfo) - dt).days
                    if age_days > 180:
                        freshness_ok = False
                except Exception:
                    pass
            if freshness_ok:
                filtered_pages.append(p)
        if len(filtered_pages) < original_count:
            logger.info(
                "Recency gate: %d -> %d pages (trends/news query)",
                original_count, len(filtered_pages),
            )
        pages = filtered_pages if filtered_pages else pages

    # Build cited sources
    sources: list[CitedSource] = []
    high_quality = 0
    blocked = 0

    for _i, rr in enumerate(ranked[:max_sources], 1):
        sr = rr.result
        matched = next(
            (p for p in pages if normalize_url(p.url) == normalize_url(sr.url)),
            None,
        )

        if matched and matched.quality == ExtractionQuality.BLOCKED:
            blocked += 1

        if matched and matched.content_length > 100:
            if matched.quality == ExtractionQuality.HIGH:
                high_quality += 1

            sources.append(CitedSource(
                citation_id=rr.citation_id,
                url=matched.final_url or matched.url,
                title=matched.title or sr.title,
                snippet=sr.snippet,
                content=matched.text,
                markdown=matched.markdown,
                content_length=matched.content_length,
                fetch_ms=matched.fetch_duration_ms,
                quality=matched.quality.value if matched.quality else "",
                content_type=matched.content_type.value if matched.content_type else "",
                source_type=matched.source_type.value if matched.source_type else sr.source_type.value,
                is_primary=matched.is_primary or sr.is_primary,
                internal_links=matched.internal_links,
                external_links=matched.external_links,
                code_languages=matched.code_languages,
                api_signatures=matched.api_signatures,
                package_refs=getattr(matched, 'package_refs', []),
                code_to_text_ratio=matched.code_to_text_ratio,
                published_date=matched.published_date,
                last_updated=matched.last_updated,
                crawled_at=matched.crawled_at,
                freshness_days=matched.freshness_days,
                is_api_reference=matched.is_api_reference,
                is_tutorial=matched.is_tutorial,
                is_error_solution=matched.is_error_solution,
                relevance_score=rr.final_score,
                authority_boost=is_authority_domain(matched.url),
                engines_found=sr.engines_found,
                github_meta=matched.github_meta,
            ))
        elif sr.snippet:
            # Fallback to snippet-only source
            sources.append(CitedSource(
                citation_id=rr.citation_id,
                url=sr.url,
                title=sr.title,
                snippet=sr.snippet,
                quality="empty",
                content_type=sr.likely_content_type.value if sr.likely_content_type else "",
                source_type=sr.source_type.value,
                is_primary=sr.is_primary,
                relevance_score=rr.final_score,
                authority_boost=is_authority_domain(sr.url),
                engines_found=sr.engines_found,
            ))

    # Phase 5: Follow links (optional)
    if follow_links and len(sources) < max_sources:
        fetched_urls = {normalize_url(s.url) for s in sources}
        all_external: list[str] = []

        for src in sources:
            for link in src.external_links:
                u = link.get("url", "")
                if u and not should_skip_url(u) and normalize_url(u) not in fetched_urls:
                    all_external.append(u)

        all_external = deduplicate_urls(all_external)
        new_urls = all_external[:max_sources - len(sources)]

        if new_urls:
            linked_pages = await _fetch_pages(new_urls, primary_engine, stealth=True)
            linked_pages = rank_pages(linked_pages, query)
            for lp in linked_pages:
                if lp.content_length > 200:
                    if lp.quality == ExtractionQuality.HIGH:
                        high_quality += 1

                    next_id = len(sources) + 1
                    source_type, is_primary = guess_source_type_and_primary(lp.url, lp.text[:300])
                    sources.append(CitedSource(
                        citation_id=next_id,
                        url=lp.final_url or lp.url,
                        title=lp.title,
                        content=lp.text,
                        markdown=lp.markdown,
                        content_length=lp.content_length,
                        fetch_ms=lp.fetch_duration_ms,
                        quality=lp.quality.value if lp.quality else "",
                        content_type=lp.content_type.value if lp.content_type else "",
                        source_type=source_type.value,
                        is_primary=is_primary,
                        internal_links=lp.internal_links,
                        external_links=lp.external_links,
                        code_languages=lp.code_languages,
                        api_signatures=lp.api_signatures,
                        package_refs=getattr(lp, 'package_refs', []),
                        code_to_text_ratio=lp.code_to_text_ratio,
                        published_date=lp.published_date,
                        last_updated=lp.last_updated,
                        crawled_at=lp.crawled_at,
                        freshness_days=lp.freshness_days,
                        is_api_reference=lp.is_api_reference,
                        is_tutorial=lp.is_tutorial,
                        is_error_solution=lp.is_error_solution,
                        relevance_score=0.5,
                        authority_boost=is_authority_domain(lp.url),
                        github_meta=lp.github_meta,
                    ))

    elapsed = (time.monotonic() - t0) * 1000

    # Smart token allocation
    allocations, sources_summarized, sources_dropped = _allocate_tokens(
        sources[:max_sources],
        max_tokens_per_source,
        max_total_tokens,
        summarize,
    )

    # Apply allocations to sources
    allocated_sources = []
    for src, budget in allocations:
        if summarize and len(src.markdown) > budget * 4:
            src.markdown = _extractive_summarize(src.markdown, budget, query)
        allocated_sources.append(src)

    # ── Citation renumbering: ensure sequential, stable IDs ──
    if allocated_sources:
        old_to_new: dict[int, int] = {}
        for new_id, src in enumerate(allocated_sources, 1):
            old_to_new[src.citation_id] = new_id
            src.citation_id = new_id

        # Update any synthesized answer that already exists (from cache)
        # and prepare for fresh synthesis with stable IDs
        def _renumber_citations(text: str, mapping: dict[int, int]) -> str:
            if not text:
                return text
            def _repl(m):
                try:
                    old = int(m.group(1))
                    new = mapping.get(old, old)
                    return f"[{new}]"
                except ValueError:
                    return m.group(0)
            return re.sub(r"\[(\d+)\]", _repl, text)

        # If we had a cached answer, renumber it (not applicable here,
        # but kept for completeness if answer synthesis changes)
        pass  # Fresh synthesis below uses already-renumbered sources

    # Answer synthesis (now with stable, sequential IDs)
    synthesized = ""
    if synthesize_answer and allocated_sources:
        synthesized = _synthesize_answer(query, allocated_sources)

    # Gap detection for follow-up research
    suggested_followups = detect_gaps(query, allocated_sources)

    result = ResearchResult(
        query=query,
        engine=engine,
        total_sources=len(allocated_sources),
        sources=allocated_sources,
        elapsed_ms=elapsed,
        high_quality_count=high_quality,
        blocked_count=blocked,
        subqueries=subqueries,
        tokens_allocated=sum(budget for _, budget in allocations),
        sources_summarized=sources_summarized,
        sources_dropped=sources_dropped,
        synthesized_answer=synthesized,
        has_answer=bool(synthesized),
        suggested_followups=suggested_followups,
    )

    # Persist to knowledge store
    if use_knowledge_store:
        try:
            from ..harness.persistence import KnowledgeStore
            store = KnowledgeStore()
            sources_json = []
            for s in allocated_sources:
                sources_json.append({
                    "citation_id": s.citation_id,
                    "url": s.url,
                    "title": s.title,
                    "snippet": s.snippet,
                    "content": s.content[:2000],
                    "markdown": s.markdown[:2000],
                    "quality": s.quality,
                })
            store.save(
                query=query,
                answer=synthesized or "",
                sources=sources_json,
            )
            logger.info("Persisted research result to knowledge store")
        except Exception as exc:
            logger.debug("Failed to persist to knowledge store: %s", exc)

    return result


def _classify_query(query: str) -> str:
    """Classify query type for synthesis strategy selection."""
    lower = query.lower()
    if any(k in lower for k in [" vs ", " versus ", "compare", "comparison", "difference between", "diff between"]):
        return "comparison"
    if any(k in lower for k in ["how to ", "install ", "setup ", "configure ", "deploy ", "getting started", "tutorial", "guide"]):
        return "howto"
    if any(k in lower for k in ["error", "fix", "deprecated", "removed", "alternative", "migrate", "troubleshoot", "issue", "problem", "bug", "solution"]):
        return "problem"
    if any(k in lower for k in ["what is ", "meaning of", "define ", "definition"]):
        return "definition"
    if any(k in lower for k in ["latest", "new ", "2025", "2026", "2027", "recent", "update", "news", "trends", "trend", "state of", "landscape", "ecosystem"]):
        return "news"
    return "general"


_CURRENT_YEAR = datetime.now().year


def _extract_key_sentences(text: str, query_keywords: set[str], max_sentences: int = 3, query: str = "") -> list[str]:
    """Extract sentences most relevant to query keywords from cleaned text.

    Preprocesses markdown to remove headings, code blocks, and boilerplate
    before extracting information-dense sentences. Optionally uses semantic
    embeddings for relevance scoring when sentence-transformers is installed.
    """
    import re

    # 1. Preprocess: remove markdown artifacts
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', ' ', text)
    # Remove markdown headings entirely
    text = re.sub(r'^#+.*$', ' ', text, flags=re.MULTILINE)
    # Remove boilerplate markers
    text = text.replace('_[Content summarized for brevity]_', ' ')
    text = text.replace('*Disclaimer:', ' ')
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # 2. Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # 3. Pre-compute semantic similarities (batch, optional)
    semantic_sims: dict[str, float] = {}
    if query:
        try:
            from .semantic_ranker import SemanticRanker
            if SemanticRanker.available():
                candidates = [
                    sent.strip() for sent in sentences
                    if 40 <= len(sent.strip()) <= 350
                ]
                if candidates:
                    sims = SemanticRanker.query_sentence_similarity_batch(query, candidates)
                    for sent, sim in zip(candidates, sims, strict=False):
                        semantic_sims[sent] = sim
        except Exception:
            pass

    scored: list[tuple[float, str]] = []
    seen: set[str] = set()

    for idx, sent in enumerate(sentences):
        sent_clean = sent.strip()
        if len(sent_clean) < 30 or len(sent_clean) > 350:
            continue
        # Skip fragments and boilerplate
        if sent_clean.startswith('URL:') or sent_clean.startswith('Links:') or sent_clean.startswith('_Links:'):
            continue
        # Skip code-like sentences
        code_starters = ('fn ', 'use ', 'struct ', 'impl ', 'mod ', 'let ', 'const ', 'pub ', 'async fn', 'println!', 'match ', 'enum ', 'type ', 'trait ', '#[', 'import ', 'from ', 'class ', 'def ', 'var ', 'const ')
        if any(sent_clean.lower().startswith(cs) for cs in code_starters):
            continue
        # Skip sentences with too many symbols (likely code/config)
        if sum(1 for c in sent_clean if c in '{}[]()<>|=&;@') > 8:
            continue
        if sent_clean in seen:
            continue
        seen.add(sent_clean)

        # Score by keyword overlap
        sent_words = set(re.findall(r'\b[a-zA-Z]+\b', sent_clean.lower()))
        overlap = len(sent_words & query_keywords) / max(len(query_keywords), 1)

        # Semantic relevance boost (optional)
        semantic_boost = semantic_sims.get(sent_clean, 0.0) * 0.6

        # Boost factors
        boost = 0.0
        # Numbers/dates/versions indicate factual density
        if re.search(r'\d{4}|v\d+\.\d+|version \d+|\d+%|\d+x', sent_clean):
            boost += 0.8
        # Definition patterns
        if re.search(r'\b(is a|are a|provides|offers|supports|requires|enables|allows|consists of|refers to)\b', sent_clean.lower()):
            boost += 0.5
        # Contrast/comparison patterns
        if re.search(r'\b(vs|versus|compared to|unlike|while|whereas|however|but|although)\b', sent_clean.lower()):
            boost += 0.4
        # Structural keywords
        if any(k in sent_clean.lower() for k in ["deprecated", "removed", "replaced", "alternative", "recommended", "best practice"]):
            boost += 0.4
        # Penalize first sentence (often intro/generic)
        if idx == 0:
            boost -= 0.2
        # Penalize overly generic sentences
        generic_starters = {"this article", "in this post", "we will", "let's", "in this guide", "before we", "today we"}
        if any(sent_clean.lower().startswith(s) for s in generic_starters):
            boost -= 0.4

        scored.append((overlap + boost + semantic_boost, sent_clean))

    scored.sort(reverse=True)
    return [s for _, s in scored[:max_sentences]]


def _deduplicate_insights(insights: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Remove near-duplicate insights using Jaccard similarity."""
    unique: list[tuple[str, int]] = []
    for text, cid in insights:
        is_dup = False
        for utext, _ in unique:
            sim = _jaccard_similarity(text, utext)
            if sim > 0.65:
                is_dup = True
                break
        if not is_dup:
            unique.append((text, cid))
    return unique


def _synthesize_answer(query: str, sources: list[CitedSource]) -> str:
    """Generate a structured, query-type-aware synthesized answer.

    Improved synthesis with topic clustering and logical flow:
    1. Sort sources by authority + relevance
    2. Extract key sentences grouped by topic
    3. Build query-type-aware structure with logical sections
    """
    if not sources:
        return ""

    query_type = _classify_query(query)
    query_keywords = set(extract_keywords(query))
    if not query_keywords:
        query_keywords = set(query.lower().split())

    # Sort sources by authority + relevance (authority-first)
    sorted_sources = sorted(
        sources,
        key=lambda s: (
            (2.0 if s.authority_boost else 0.0)
            + (1.0 if s.is_primary else 0.0)
            + (s.relevance_score * 0.5)
            + {"high": 1.0, "medium": 0.5, "low": 0.2, "empty": 0.0}.get(s.quality, 0.0)
        ),
        reverse=True,
    )

    # Extract and tag insights by topic
    topic_buckets: dict[str, list[tuple[str, int]]] = {
        "definition": [],
        "current_state": [],
        "comparison": [],
        "performance": [],
        "issues": [],
        "outlook": [],
        "general": [],
    }

    seen_sentences: set[str] = set()

    for src in sorted_sources:
        text = src.content or src.markdown or src.snippet
        if not text:
            continue

        key_sents = _extract_key_sentences(text, query_keywords, max_sentences=3, query=query)
        for sent in key_sents:
            sent_lower = sent.lower()
            # Skip duplicates
            if sent in seen_sentences:
                continue
            seen_sentences.add(sent)

            # Tag by topic
            if any(w in sent_lower for w in ["is a", "refers to", "means", "definition", "describes"]):
                bucket = "definition"
            elif any(w in sent_lower for w in ["vs", "versus", "compared to", "unlike", "whereas", "alternative"]):
                bucket = "comparison"
            elif any(w in sent_lower for w in ["faster", "slower", "performance", "latency", "throughput", "benchmark", "memory", "cpu"]):
                bucket = "performance"
            elif any(w in sent_lower for w in ["deprecated", "removed", "issue", "bug", "error", "problem", "fix", "broken"]):
                bucket = "issues"
            elif any(w in sent_lower for w in ["future", "upcoming", "planned", "roadmap", "will be", "next year", "2027", "trend"]):
                bucket = "outlook"
            elif any(w in sent_lower for w in ["currently", "now", "in 2026", "adoption", "usage", "popular", "market share"]):
                bucket = "current_state"
            else:
                bucket = "general"

            topic_buckets[bucket].append((sent, src.citation_id))

    # Build answer with logical flow based on query type
    answer_parts: list[str] = []

    def _add_section(title: str, items: list[tuple[str, int]], max_items: int = 4):
        if not items:
            return
        answer_parts.append(f"**{title}**")
        answer_parts.append("")
        for text, cid in items[:max_items]:
            answer_parts.append(f"- {text} [{cid}]")
        answer_parts.append("")

    if query_type == "definition":
        answer_parts.append(f"### Definition: {query}")
        answer_parts.append("")
        _add_section("What it is", topic_buckets["definition"])
        _add_section("How it works", topic_buckets["general"])
        _add_section("Current adoption", topic_buckets["current_state"])

    elif query_type == "comparison":
        answer_parts.append(f"### Comparison: {query}")
        answer_parts.append("")
        _add_section("Key differences", topic_buckets["comparison"])
        _add_section("Performance", topic_buckets["performance"])
        _add_section("Current landscape", topic_buckets["current_state"])

    elif query_type == "howto":
        answer_parts.append(f"### Guide: {query}")
        answer_parts.append("")
        _add_section("Overview", topic_buckets["definition"])
        _add_section("Steps", topic_buckets["general"])
        _add_section("Common issues", topic_buckets["issues"])

    elif query_type == "problem":
        answer_parts.append(f"### Problem & Solution: {query}")
        answer_parts.append("")
        _add_section("Situation", topic_buckets["general"][:1])
        _add_section("Known issues", topic_buckets["issues"])
        _add_section("Recommendations", topic_buckets["current_state"])

    else:  # general / news / trends
        answer_parts.append(f"### Key Findings: {query}")
        answer_parts.append("")
        _add_section("Current state", topic_buckets["current_state"])
        _add_section("Performance & benchmarks", topic_buckets["performance"])
        _add_section("Comparisons", topic_buckets["comparison"])
        _add_section("Known issues", topic_buckets["issues"])
        _add_section("Outlook", topic_buckets["outlook"])

    answer_parts.append("---")
    answer_parts.append("")

    return "\n".join(answer_parts)


def _allocate_tokens(
    sources: list[CitedSource],
    max_tokens_per_source: int,
    max_total_tokens: int,
    summarize: bool,
) -> tuple[list[tuple[CitedSource, int]], int, int]:
    """Allocate tokens to sources based on quality scores."""
    if not sources:
        return [], 0, 0

    quality_weights = {"high": 1.0, "medium": 0.7, "low": 0.4, "empty": 0.2, "blocked": 0.0}
    scored_sources = [
        (src, quality_weights.get(src.quality, 0.5) * (1 + src.relevance_score))
        for src in sources
    ]
    scored_sources.sort(key=lambda x: x[1], reverse=True)

    allocations = []
    total_allocated = 0
    sources_summarized = 0
    sources_dropped = 0

    for src, _score in scored_sources:
        if src.quality == "blocked":
            continue

        quality_mult = quality_weights.get(src.quality, 0.5)
        budget = int(max_tokens_per_source * quality_mult)

        if total_allocated + budget > max_total_tokens:
            if summarize and src.quality in ("medium", "low"):
                budget = int(budget * 0.5)
                if total_allocated + budget <= max_total_tokens:
                    allocations.append((src, budget))
                    total_allocated += budget
                    sources_summarized += 1
                    continue

            sources_dropped += 1
            continue

        allocations.append((src, budget))
        total_allocated += budget

    return allocations, sources_summarized, sources_dropped


def _extractive_summarize(markdown: str, max_tokens: int, query: str = "") -> str:
    """Create extractive summary using headings and key paragraphs.

    Query-aware: sections containing query keywords retain more sentences.
    """
    from ..extraction.content import estimate_token_count

    if estimate_token_count(markdown) <= max_tokens:
        return markdown

    query_keywords = set(extract_keywords(query)) if query else set()

    summary_parts = []
    lines = markdown.split('\n')
    current_section = []
    in_section = False
    section_has_keyword = False

    for line in lines:
        if line.startswith('#'):
            if current_section:
                limit = 4 if section_has_keyword else 2
                summary_parts.extend(current_section[:limit])
                current_section = []
            in_section = True
            current_section.append(line)
            section_has_keyword = bool(
                query_keywords and query_keywords & set(re.findall(r'\b[a-zA-Z]+\b', line.lower()))
            )
        elif in_section and line.strip() and not line.startswith('#'):
            current_section.append(line)
            if query_keywords and not section_has_keyword:
                section_has_keyword = bool(
                    query_keywords & set(re.findall(r'\b[a-zA-Z]+\b', line.lower()))
                )
            if len(current_section) >= 8:
                in_section = False

    if current_section:
        limit = 4 if section_has_keyword else 2
        summary_parts.extend(current_section[:limit])

    summary = '\n\n'.join(summary_parts)

    if estimate_token_count(summary) > max_tokens:
        summary = truncate_for_llm(summary, max_tokens)

    return summary + "\n\n_[Content summarized for brevity]_"


# ── Spam / SEO blog domain blacklist ──
_SPAM_DOMAINS = {
    # Low-quality SEO aggregators and bootcamp marketing blogs
    "nucamp.co", "pillaiinfotech.com", "indiit.com", "cloudbuzz.ai",
    "acemindtech.com", "solutionsuggest.com", "geeksforgeeks.org",
    "tutorialspoint.com", "javatpoint.com", "w3schools.com",
    "simplilearn.com", "intellipaat.com", "edureka.co",
    # Redirect / placeholder pages
    "google.com", "bing.com", "yahoo.com",
}

# Authority tier for scoring
_AUTHORITY_TIER1 = {
    "github.com", "gitlab.com", "stackoverflow.com", "stackexchange.com",
    "docs.python.org", "developer.mozilla.org", "react.dev", "nextjs.org",
    "nodejs.org", "go.dev", "pkg.go.dev", "doc.rust-lang.org", "docs.rs",
    "learn.microsoft.com", "postgresql.org", "kubernetes.io", "fastapi.tiangolo.com",
    "docs.djangoproject.com", "vuejs.org", "svelte.dev", "angular.io",
    "astro.build", "kit.svelte.dev", "remix.run", "nuxt.com",
    "docs.astro.build", "trpc.io", "prisma.io", "orm.drizzle.team",
    "turso.tech", "neon.tech", "planetscale.com", "vercel.com",
    "cloudflare.com", "workers.cloudflare.com", "aws.amazon.com",
    "openai.com", "platform.openai.com", "anthropic.com", "claude.ai",
    "docs.anthropic.com", "ai.google.dev", "gemini.google.com",
    "arxiv.org", "semanticscholar.org", "scholar.google.com",
    "ieee.org", "acm.org", "usenix.org",
    "npmjs.com", "pypi.org", "crates.io", "pkg.go.dev",
    "huggingface.co", "paperswithcode.com",
}


def _prioritize_urls(urls: list[str]) -> list[str]:
    """Sort URLs so high-trust domains are fetched first.

    Filters out known spam/SEO domains and penalizes low-authority blogs.
    """
    from ..utils.url import get_domain

    def _score(url: str) -> int:
        domain = get_domain(url)
        # Spam domains: discard (return high score so they sort last, then we filter)
        if any(d in domain for d in _SPAM_DOMAINS):
            return 999
        # Tier 1 authority
        if any(d in domain for d in _AUTHORITY_TIER1):
            return 0
        if domain.endswith((".edu", ".gov", ".ac.kr", ".go.kr", ".or.kr")):
            return 1
        # Developer-focused platforms
        if any(d in domain for d in ["medium.com", "dev.to", "blog.", "tistory.com", "velog.io"]):
            return 3
        return 2

    scored = [(u, _score(u)) for u in urls]
    # Filter out spam (score 999)
    scored = [(u, s) for u, s in scored if s < 900]
    scored.sort(key=lambda x: x[1])
    return [u for u, _ in scored]


async def _probe_network(engine) -> dict:
    """Probe network latency with a fast, reliable URL."""
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(
            engine.fetch("https://lite.duckduckgo.com", timeout=3.0),
            timeout=5.0,
        )
        elapsed = (time.monotonic() - t0) * 1000
        return {"ok": True, "latency_ms": elapsed, "slow": elapsed > 5000}
    except Exception:
        elapsed = (time.monotonic() - t0) * 1000
        return {"ok": False, "latency_ms": elapsed, "slow": True}


def _filter_slow_domains(urls: list[str], store=None, max_fail_rate: float = 0.8) -> list[str]:
    """Filter out URLs from domains with poor fetch history."""
    if not store:
        return urls
    filtered = []
    for url in urls:
        domain = get_domain(url)
        stats = store.get_domain_stats(domain)
        if stats and stats["success_rate"] < (1 - max_fail_rate) and stats["total"] >= 3:
            logger.debug("Skip slow domain %s (rate=%.0f%%)", domain, stats["success_rate"] * 100)
            continue
        filtered.append(url)
    return filtered


async def _fetch_pages(
    urls: list[str],
    engine,
    stealth: bool = False,
    max_concurrent: int = 5,
    min_quality_results: int = 3,
    timeout_per_fetch: float = 5.0,
) -> list[PageContent]:
    """Fetch multiple pages with fast abort.

    Uses asyncio.as_completed so fast sites return immediately.
    Cancels remaining tasks once enough high-quality results are collected.
    """
    sem = asyncio.Semaphore(max_concurrent)
    results: list[PageContent] = []

    async def _one(u: str) -> PageContent:
        async with sem:
            try:
                return await asyncio.wait_for(
                    engine.fetch(u, stealth=stealth, timeout=timeout_per_fetch),
                    timeout=timeout_per_fetch + 2.0,
                )
            except asyncio.TimeoutError:
                return PageContent(
                    url=u,
                    error_message=f"Timeout after {timeout_per_fetch}s",
                    quality=ExtractionQuality.BLOCKED,
                    fetch_duration_ms=int(timeout_per_fetch * 1000),
                )
            except Exception as exc:
                logger.warning("Fetch failed for %s: %s", u, exc)
                return PageContent(
                    url=u,
                    error_message=str(exc),
                    quality=ExtractionQuality.BLOCKED,
                )

    pending = [asyncio.create_task(_one(u)) for u in urls]

    try:
        for coro in asyncio.as_completed(pending, timeout=30.0):
            try:
                page = await coro
                results.append(page)
                # Fast abort: enough high-quality results?
                good = sum(
                    1 for r in results
                    if r.quality == ExtractionQuality.HIGH and r.content_length > 200
                )
                if good >= min_quality_results and len(results) >= min_quality_results + 1:
                    logger.info("Fast abort: %d high-quality pages fetched", good)
                    break
            except asyncio.CancelledError:
                pass
    except asyncio.TimeoutError:
        logger.warning("Overall fetch pipeline timeout after 30s")
    finally:
        # Cancel any remaining tasks and wait for cleanup
        for task in pending:
            if not task.done():
                task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    # Drain any remaining tasks
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    return results


def format_for_llm(
    result: ResearchResult,
    max_tokens_per_source: int = 2500,
    max_total_tokens: int = 20000,
    summarize: bool = False,
) -> str:
    """Format research results into token-efficient markdown with citations.

    Perplexity-style output with inline citations [1], [2] and
    quality metadata for the host LLM."""
    if not result.sources:
        return f"No results found for: '{result.query}' ({result.engine})"

    lines: list[str] = []

    # Header with stats
    quality_summary = ""
    if result.high_quality_count or result.blocked_count:
        parts = []
        if result.high_quality_count:
            parts.append(f"{result.high_quality_count} high-quality")
        if result.blocked_count:
            parts.append(f"{result.blocked_count} blocked")
        quality_summary = f" | {' ,'.join(parts)}"

    lines.append(f"## Research: {result.query}")
    lines.append(
        f"_engine: {result.engine} | sources: {result.total_sources}{quality_summary} | {result.elapsed_ms:.0f}ms_"
    )

    if result.subqueries and len(result.subqueries) > 1:
        lines.append(f"_subqueries: {', '.join(result.subqueries)}_")

    lines.append("")

    # Synthesized answer (Perplexity-style)
    if result.has_answer and result.synthesized_answer:
        lines.append(result.synthesized_answer)

    # Suggested follow-ups
    if result.suggested_followups:
        lines.append("### Suggested Follow-up Research")
        lines.append("")
        for sq in result.suggested_followups:
            lines.append(f"- {sq}")
        lines.append("")

    # Sources with citations
    lines.append("### Sources")
    lines.append("")

    for src in result.sources:
        # Minimal badge: only show HIGH quality and freshness
        badge = " **[HIGH]**" if src.quality == "high" else ""

        freshness = ""
        if src.freshness_days is not None:
            if src.freshness_days > 365:
                freshness = f" | age: {src.freshness_days // 30}mo"
            else:
                freshness = f" | age: {src.freshness_days}d"
        elif src.published_date:
            freshness = f" | {src.published_date}"

        authority = " | 🔒" if src.authority_boost else ""
        cross_engine = f" | ✓{len(src.engines_found)}" if len(src.engines_found) > 1 else ""

        lines.append(
            f"#### [{src.citation_id}] {src.title}{badge}{freshness}{authority}{cross_engine}"
        )
        lines.append(f"{src.url}")

        if src.github_meta and "stars" in src.github_meta:
            gm = src.github_meta
            gh_info = f"⭐ {gm['stars']}"
            if "last_updated" in gm:
                gh_info += f" | updated {gm['last_updated'][:10]}"
            lines.append(f"_{gh_info}_")

        if src.markdown:
            content = truncate_for_llm(src.markdown, max_tokens_per_source)
        elif src.content:
            content = truncate_for_llm(src.content, max_tokens_per_source)
        elif src.snippet:
            content = src.snippet
        else:
            content = "_no content extracted_"

        lines.append(f"\n{content}\n")

    return "\n".join(lines)


def normalize_url(url: str) -> str:
    """Simple normalization for deduplication."""
    from ..utils.url import normalize_url as _normalize
    return _normalize(url)
