"""MCP tool definitions — universal AI search with Perplexity-level quality.

Every tool response includes rich metadata (quality scores, content types,
citations, link maps) so the host LLM can make informed decisions."""

from __future__ import annotations

import asyncio
import logging
import re

from .config import DEFAULT_CONFIG
from .engines.base import SearchEngine
from .engines.registry import SearchEngineRegistry
from .exceptions import MaruSearchError, QueryRejectedError
from .extraction.content import truncate_for_llm
from .research.deep import deep_research, format_for_llm
from .research.fetch_planner import plan_reads
from .research.pipeline import (
    answer_quality_suffix,
    append_research_footer,
    persist_research_artifacts,
    save_research_knowledge,
)
from .research.ranker import rank_pages
from .utils.cache import cache_key, fetch_page_cache_key, get_fetch_cache, get_search_cache
from .utils.locale_harness import optimize_for_engine
from .utils.query_gate import (
    QueryPrepResult,
    format_query_meta,
    format_query_rejection,
    prepare_search_query,
)
from .utils.sanitize import (
    analyze_content,
    unwrap_external_content,
    wrap_external_content,
    wrap_serp_content,
)

logger = logging.getLogger(__name__)
logging.getLogger("scrapling").setLevel(logging.WARNING)
logging.getLogger("scrapling.fetchers").setLevel(logging.WARNING)

# All registered engines
SEARCH_ENGINES = SearchEngineRegistry.list_engines()


def _coerce_registered_engine(engine: str) -> str:
    """Return *engine* if registered, else ``DEFAULT_CONFIG.default_engine`` or DDG."""
    if engine in SEARCH_ENGINES:
        return engine
    fb = DEFAULT_CONFIG.default_engine
    if fb in SEARCH_ENGINES:
        return fb
    return "duckduckgo_lite"


def _fetch_engine() -> SearchEngine:
    """Fetch engine instance (separate CB from SERP search when registered)."""
    name = "duckduckgo_fetch"
    if name not in SEARCH_ENGINES:
        name = "duckduckgo_lite"
    return SearchEngineRegistry.create(name)


def _cap_knowledge_answer(text: str) -> str:
    cap = DEFAULT_CONFIG.knowledge_reuse_max_chars
    if len(text) <= cap:
        return text
    return text[:cap] + "\n\n_[cached research truncated — run fresh deep_research if needed]_"


async def _fetch_body_markdown(
    url: str,
    *,
    stealth: bool = False,
    max_tokens: int = 600,
) -> str:
    """Fetch extractable body without the external-content security wrapper."""
    from .utils.url import normalize_url

    norm_url = normalize_url(url)
    cache = get_fetch_cache()
    key = fetch_page_cache_key(norm_url, stealth, max_tokens) + "|body"
    cached = cache.get(key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    fetch_timeout = DEFAULT_CONFIG.http_fetch_timeout_seconds
    engine = _fetch_engine()
    page = await asyncio.wait_for(
        engine.fetch(url, stealth=stealth),
        timeout=fetch_timeout,
    )
    if page.quality.value == "blocked" or page.content_length == 0:
        raise MaruSearchError(page.error_message or "fetch blocked or empty")

    content = page.markdown if page.markdown else page.text
    body = truncate_for_llm(content, max_tokens)
    cache.set(key, body)
    _record_fetch_domain(url, page.fetch_duration_ms, success=True)
    return body


async def _parallel_auto_fetch_previews(
    sources: list,
    *,
    preview_chars: int = 800,
    max_tokens: int = 600,
) -> list[str]:
    """Fetch source bodies in parallel for auto_fetch previews."""
    timeout = DEFAULT_CONFIG.auto_fetch_nested_timeout_seconds
    sem = asyncio.Semaphore(DEFAULT_CONFIG.max_concurrent_fetches)

    async def _one(src: object) -> list[str]:
        async with sem:
            lines: list[str] = []
            try:
                body = await asyncio.wait_for(
                    _fetch_body_markdown(src.url, max_tokens=max_tokens),  # type: ignore[attr-defined]
                    timeout=timeout,
                )
                preview = body[:preview_chars] if len(body) > preview_chars else body
                lines.append(f"**From [{src.citation_id}] {src.title}**")  # type: ignore[attr-defined]
                lines.append(f"<{src.url}>")  # type: ignore[attr-defined]
                lines.append("")
                lines.append(preview)
                if len(body) > preview_chars:
                    lines.append("\n... (truncated)")
                lines.append("")
            except Exception as exc:
                logger.debug("Auto-fetch failed for %s: %s", getattr(src, "url", ""), exc)
                lines.append(
                    f"**From [{getattr(src, 'citation_id', '?')}] {getattr(src, 'title', '')}** — fetch failed"
                )
                lines.append("")
            return lines

    chunks = await asyncio.gather(*(_one(s) for s in sources))
    return [line for block in chunks for line in block]


async def _parallel_answer_evidence(
    sources: list,
    *,
    fetch_budget: int,
) -> tuple[list[str], int]:
    """Parallel fetch for answer() evidence section."""
    timeout = DEFAULT_CONFIG.auto_fetch_nested_timeout_seconds
    sem = asyncio.Semaphore(DEFAULT_CONFIG.max_concurrent_fetches)

    async def _one(src: object) -> tuple[list[str], int]:
        async with sem:
            lines: list[str] = []
            try:
                body = await asyncio.wait_for(
                    _fetch_body_markdown(
                        src.url,  # type: ignore[attr-defined]
                        max_tokens=max(250, min(fetch_budget, 1800)),
                    ),
                    timeout=timeout,
                )
                preview = truncate_for_llm(body, max_tokens=max(250, min(fetch_budget, 1800)))
                lines.append(f"#### [{src.citation_id}] {src.title}")  # type: ignore[attr-defined]
                lines.append(f"URL: {src.url}")  # type: ignore[attr-defined]
                lines.append("")
                lines.append(preview)
                lines.append("")
                return lines, 1
            except Exception as exc:
                logger.debug("answer auto-fetch failed for %s: %s", getattr(src, "url", ""), exc)
                lines.append(
                    f"#### [{getattr(src, 'citation_id', '?')}] {getattr(src, 'title', '')} — fetch failed"
                )
                lines.append(f"URL: {getattr(src, 'url', '')}")
                lines.append("")
                return lines, 0

    chunks = await asyncio.gather(*(_one(s) for s in sources))
    flat = [line for block, _ in chunks for line in block]
    fetched = sum(ok for _, ok in chunks)
    return flat, fetched


def _record_fetch_domain(url: str, duration_ms: float, *, success: bool) -> None:
    try:
        from .harness.persistence import KnowledgeStore
        from .utils.url import get_domain

        KnowledgeStore().record_domain_fetch(get_domain(url), duration_ms, success)
    except Exception:
        pass


def require_engine_query(query: str) -> tuple[str, QueryPrepResult]:
    """Validate/optimize *query* or raise QueryRejectedError for the host agent."""
    prep = prepare_search_query(query)
    if not prep.passed_gate:
        raise QueryRejectedError(format_query_rejection(prep))
    return prep.query, prep


# ═══════════════════════════════════════════════════════════════
# Tool: web_search
# ═══════════════════════════════════════════════════════════════


async def tool_web_search(
    query: str,
    engine: str = DEFAULT_CONFIG.default_engine,
    max_results: int = DEFAULT_CONFIG.max_results_per_query,
) -> str:
    """Search by scraping a search engine's HTML results page directly.

    No API keys, no rate limits. Scrapling handles anti-bot bypass.
    Returns content type hints and citation IDs per result so the LLM
    can prioritize and cite sources.
    """
    query, prep = require_engine_query(query)

    engine = _coerce_registered_engine(engine)

    serp_timeout = DEFAULT_CONFIG.serp_timeout_seconds
    used_engine = engine

    # Check cache
    cache = get_search_cache()
    key = cache_key("web_search", engine, str(max_results), query)
    cached = cache.get(key)
    if cached is not None:
        logger.debug("Cache hit for web_search: %s", query)
        return cached  # type: ignore[no-any-return]

    try:
        search_engine = SearchEngineRegistry.create(engine)
        # Locale-aware query optimization for region-specific engines
        optimized_query = optimize_for_engine(query, engine)
        results = await asyncio.wait_for(
            search_engine.search(optimized_query, max_results=max_results),
            timeout=serp_timeout,
        )
    except asyncio.TimeoutError:
        return (
            f"## [TIMEOUT] Search for '{query}' exceeded {serp_timeout:.0f} seconds.\n\n"
            "_The search engine may be slow or blocked.\n"
            "Try a different engine or a more specific query._"
        )
    except MaruSearchError as e:
        if e.suggested_engine and e.suggested_engine != engine:
            logger.info("Falling back to %s", e.suggested_engine)
            used_engine = e.suggested_engine
            search_engine = SearchEngineRegistry.create(e.suggested_engine)
            fb_query = optimize_for_engine(query, e.suggested_engine)
            try:
                results = await asyncio.wait_for(
                    search_engine.search(fb_query, max_results=max_results),
                    timeout=serp_timeout,
                )
            except asyncio.TimeoutError:
                return (
                    f"## [TIMEOUT] Search for '{query}' exceeded {serp_timeout:.0f} seconds "
                    f"(fallback engine {used_engine}).\n\n"
                    "_The search engine may be slow or blocked.\n"
                    "Try a different engine or a more specific query._"
                )
        else:
            raise

    if not results:
        return f"No results found for: {query}"

    # Assign citation IDs
    for i, r in enumerate(results, 1):
        r.citation_id = i

    lines = [f"Search: **{query}**  _engine={used_engine}_\n"]
    for r in results:
        type_badge = (
            f" [{r.likely_content_type.value}]" if r.likely_content_type.value != "unknown" else ""
        )
        source_badge = ""
        if r.source_type and r.source_type.value != "unknown":
            source_badge = f" [{r.source_type.value.upper().replace('_', '-')}]"
        primary_badge = " [PRIMARY]" if r.is_primary else ""
        auth_badge = (
            " [AUTHORITY]"
            if any(
                d in r.domain
                for d in [
                    "docs.python.org",
                    "developer.mozilla.org",
                    "github.com",
                    "stackoverflow.com",
                    "arxiv.org",
                ]
            )
            else ""
        )
        cite = f" [{r.citation_id}]"
        lines.append(
            f"{r.position}. **{r.title}**{cite}{type_badge}{source_badge}{primary_badge}{auth_badge}"
        )
        lines.append(f"   {r.url}")
        if r.snippet:
            lines.append(f"   > {r.snippet[:300]}")
        lines.append("")
    result_text = "\n".join(lines)
    report = analyze_content(result_text)
    result_text = wrap_serp_content(result_text, source_url=f"search:{engine}", report=report)
    result_text += format_query_meta(prep)
    if used_engine == engine:
        cache.set(key, result_text)
    return result_text


# ═══════════════════════════════════════════════════════════════
# Tool: fetch_page
# ═══════════════════════════════════════════════════════════════


async def tool_fetch_page(
    url: str,
    stealth: bool = False,
    max_tokens: int = 6000,
    auto_stealth_fallback: bool = True,
) -> str:
    """Fetch a page via Scrapling and extract clean, LLM-optimized content.

    Use Cases:
    - General web pages, blogs, documentation
    - Sites without anti-bot protection
    - When you need fast fetching (uses lightweight DynamicFetcher)

    When to use stealth=True parameter instead of stealthy_fetch:
    - Site returns CAPTCHA or access denied
    - Content appears incomplete (missing articles, blocked sections)
    - You suspect anti-bot measures but want to try fast path first

    When to use stealthy_fetch instead:
    - You already know the site has strong protection (Cloudflare, DataDome)
    - Previous fetch_page attempts failed
    - You need guaranteed access and can accept slower fetching

    Returns structured markdown with quality signals, content type,
    and link suggestions for follow-up.
    """
    # Normalize URL for consistent cache keys (strip tracking params, fragments)
    from .utils.url import normalize_url

    norm_url = normalize_url(url)

    # Check cache
    cache = get_fetch_cache()
    key = fetch_page_cache_key(norm_url, stealth, max_tokens)
    cached = cache.get(key)
    if cached is not None:
        logger.debug("Cache hit for fetch: %s", norm_url)
        return cached  # type: ignore[no-any-return]

    fetch_timeout = DEFAULT_CONFIG.http_fetch_timeout_seconds

    engine = _fetch_engine()
    try:
        page = await asyncio.wait_for(
            engine.fetch(url, stealth=stealth),
            timeout=fetch_timeout,
        )
    except asyncio.TimeoutError:
        if auto_stealth_fallback and not stealth:
            logger.info("fetch_page timeout for %s, auto-falling back to stealthy_fetch", url)
            return await tool_stealthy_fetch(url, max_tokens)
        return (
            f"## [TIMEOUT] {url}\n"
            f"_Fetch exceeded {fetch_timeout:.0f} seconds. The site may be too slow or blocked.\n"
            "Try stealthy_fetch() or a different URL._"
        )

    # Prevent memory exhaustion from unexpectedly large pages
    MAX_FETCH_BYTES = 5_000_000  # 5 MB
    raw_size = len(page.html) + len(page.text) + len(page.markdown)
    if raw_size > MAX_FETCH_BYTES:
        return (
            f"## [TOO LARGE] {url}\n"
            f"_Page content exceeds {MAX_FETCH_BYTES:,} bytes ({raw_size:,} bytes).\n"
            "The site returned an unexpectedly large response. Try a different URL._"
        )

    if page.quality.value == "blocked":
        err = page.error_message or ""
        # Auto-fallback to stealth for 403/CAPTCHA when auto_stealth_fallback is enabled
        if (
            auto_stealth_fallback
            and not stealth
            and ("403" in err or "forbidden" in err.lower() or "blocked" in err.lower())
        ):
            logger.info("fetch_page blocked for %s, auto-falling back to stealthy_fetch", url)
            return await tool_stealthy_fetch(url, max_tokens)

        # Give precise guidance based on error classification
        if "timeout" in err.lower():
            guidance = "_Server timed out. The site may be slow or overloaded. Try again later or increase timeout._"
        elif "ssl" in err.lower() or "certificate" in err.lower():
            guidance = "_SSL/TLS error. The site's certificate may be invalid or your network is intercepting TLS._"
        elif "dns" in err.lower() or "name resolution" in err.lower():
            guidance = "_DNS resolution failed. The domain may not exist or DNS is unreachable._"
        elif "connection" in err.lower() or "refused" in err.lower():
            guidance = "_Connection refused. The server may be down or blocking your IP._"
        elif "import" in err.lower() or "cannot import" in err.lower():
            guidance = (
                "_Internal fetcher error (dependency mismatch). This is a bug, not a blocked site._"
            )
        elif "403" in err or "forbidden" in err.lower() or "access denied" in err.lower():
            guidance = "_Access denied (HTTP 403). Anti-bot wall hit — try stealthy_fetch or fetch_page with stealth=True._"
        else:
            guidance = (
                "_Fetch blocked or failed. Try stealthy_fetch or fetch_page with stealth=True._"
            )
        return f"## [BLOCKED] {url}\n{guidance}\nError: {page.error_message}"

    if page.content_length == 0:
        if auto_stealth_fallback and not stealth:
            logger.info("fetch_page empty for %s, auto-falling back to stealthy_fetch", url)
            return await tool_stealthy_fetch(url, max_tokens)
        return f"## [EMPTY] {url}\n_No extractable content found._"

    content = page.markdown if page.markdown else page.text
    content = truncate_for_llm(content, max_tokens)

    quality_line = f"_quality: {page.quality.value} | type: {page.content_type.value} | {page.content_length} chars | {page.fetch_duration_ms:.0f}ms_"

    code_meta = ""
    if page.code_languages:
        code_meta += f"\n_languages: {', '.join(page.code_languages)}_"
    if page.api_signatures:
        sigs = "; ".join(s["signature"][:80] for s in page.api_signatures[:5])
        code_meta += f"\n_API signatures: {sigs}_"
    if getattr(page, "package_refs", []):
        pkgs = ", ".join(f"{p['package']} ({p['language']})" for p in page.package_refs[:5])
        code_meta += f"\n_Packages: {pkgs}_"
    if page.code_to_text_ratio > 0.1:
        code_meta += f"\n_code-to-text ratio: {page.code_to_text_ratio:.0%}_"
    if page.published_date:
        freshness = f" ({page.freshness_days}d ago)" if page.freshness_days is not None else ""
        code_meta += f"\n_published: {page.published_date}{freshness}_"
    if page.is_api_reference:
        code_meta += "\n_type: API reference_"
    elif page.is_tutorial:
        code_meta += "\n_type: tutorial_"
    elif page.is_error_solution:
        code_meta += "\n_type: error/solution_"

    link_section = ""
    if page.external_links:
        links_preview = "\n".join(
            f"- [{link['text'][:60]}]({link['url']})" for link in page.external_links[:5]
        )
        link_section = f"\n\n**Follow-up links:**\n{links_preview}"

    result_text = (
        f"## {page.title}\n"
        f"URL: {page.final_url or url}\n"
        f"{quality_line}{code_meta}\n\n"
        f"{content}"
        f"{link_section}"
    )
    report = analyze_content(result_text)
    result_text = wrap_external_content(result_text, source_url=url, report=report)
    _record_fetch_domain(url, page.fetch_duration_ms, success=True)
    cache.set(key, result_text)
    return result_text


# ═══════════════════════════════════════════════════════════════
# Tool: fetch_bulk
# ═══════════════════════════════════════════════════════════════


async def tool_fetch_bulk(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = DEFAULT_CONFIG.max_concurrent_fetches,
    max_tokens: int = 3000,
    query: str = "",
) -> str:
    """Fetch multiple URLs in parallel via Scrapling.

    Each result includes quality signals so the LLM can prioritize reading.
    """
    fetch_timeout = DEFAULT_CONFIG.http_fetch_timeout_seconds
    fetch_timeout_ms = int(fetch_timeout * 1000)

    from .utils.url import normalize_url

    engine = _fetch_engine()
    sem = asyncio.Semaphore(max_concurrent)

    async def _fetch_one(u: str):
        norm = normalize_url(u)
        cache = get_fetch_cache()
        key = fetch_page_cache_key(norm, stealth, max_tokens) + "|page"
        cached = cache.get(key)
        if cached is not None:
            logger.debug("Cache hit for fetch_bulk: %s", norm)
            return cached

        async with sem:
            try:
                page = await asyncio.wait_for(
                    engine.fetch(u, stealth=stealth),
                    timeout=fetch_timeout,
                )
                # Prevent memory exhaustion from unexpectedly large pages
                MAX_FETCH_BYTES = 5_000_000  # 5 MB per page
                raw_size = len(page.html) + len(page.text) + len(page.markdown)
                if raw_size > MAX_FETCH_BYTES:
                    from .engines.base import ExtractionQuality, PageContent

                    return PageContent(
                        url=u,
                        error_message=f"Page content exceeds {MAX_FETCH_BYTES:,} bytes",
                        quality=ExtractionQuality.BLOCKED,
                        fetch_duration_ms=0,
                    )
                cache.set(key, page)
                return page
            except asyncio.TimeoutError:
                from .engines.base import ExtractionQuality, PageContent

                return PageContent(
                    url=u,
                    error_message=f"Fetch timeout after {fetch_timeout:.0f} seconds",
                    quality=ExtractionQuality.BLOCKED,
                    fetch_duration_ms=fetch_timeout_ms,
                )

    pages = await asyncio.gather(*(_fetch_one(u) for u in urls), return_exceptions=True)
    # unwrap any stray exceptions into PageContent
    safe_pages: list = []
    for p in pages:
        if isinstance(p, Exception):
            from .engines.base import ExtractionQuality, PageContent

            safe_pages.append(
                PageContent(
                    url="",
                    error_message=str(p),
                    quality=ExtractionQuality.BLOCKED,
                )
            )
        else:
            safe_pages.append(p)
    from .engines.base import PageContent

    all_pages = [p for p in safe_pages if isinstance(p, PageContent)]
    rankable = [p for p in all_pages if p.content_length > 0]
    blocked_pages = [p for p in all_pages if p not in rankable]
    if rankable and query.strip():
        rankable = rank_pages(rankable, query)
    display_pages = rankable + blocked_pages

    lines: list[str] = []
    for i, page in enumerate(display_pages, 1):
        content = page.markdown if page.markdown else page.text
        content = truncate_for_llm(content, max_tokens)

        badge = ""
        if page.quality.value == "high":
            badge = " **[HIGH]**"
        elif page.quality.value == "blocked":
            badge = " **[BLOCKED]**"
        elif page.quality.value == "empty":
            badge = " _[empty]_"

        status = page.quality.value if page.content_length < 100 else "ok"
        error_line = ""
        if page.quality.value == "blocked" and page.error_message:
            error_line = f"\n_Error: {page.error_message}_"

        lines.append(f"### [{i}] {page.title}{badge}")
        lines.append(
            f"URL: {page.final_url or page.url} _({page.content_length} chars, {status}, {page.content_type.value})_{error_line}"
        )
        lines.append(f"\n{content}\n")

    result_text = "\n".join(lines) if lines else "No content fetched."
    report = analyze_content(result_text)
    result_text = wrap_external_content(
        result_text, source_url=f"bulk:{len(urls)} URLs", report=report
    )
    return result_text


# ═══════════════════════════════════════════════════════════════
# Tool: deep_research
# ═══════════════════════════════════════════════════════════════


async def tool_deep_research(
    query: str,
    engine: str = DEFAULT_CONFIG.default_engine,
    max_sources: int = DEFAULT_CONFIG.deep_max_sources,
    expand_queries: bool = True,
    primary_sources_only: bool = False,
    auto_fetch: int = 0,
) -> str:
    """Deep multi-engine search with query expansion and intelligent ranking.

    Searches across multiple engines with orthogonal subqueries, then merges,
    deduplicates, and ranks results by relevance and authority. Returns a
    ranked URL list with rich metadata for the agent to consume.

    The agent's LLM should:
    1. Review the ranked sources and their metadata
    2. Decide which URLs to deep-read using fetch_page or fetch_bulk
    3. Synthesize its own answer using the fetched content

    Workflow:
    1. Expand query into orthogonal subqueries for broader coverage
    2. Search original + subqueries across multiple engines
    3. Deduplicate, rank by relevance and authority (BM25 + metadata)
    4. Return ranked URLs with snippets, authority badges, and cross-engine scores

    Source Filtering:
    - primary_sources_only: Keep only official docs, GitHub, registries,
      academic papers, and Stack Overflow. Drops blogs and aggregators.
    """
    query, prep = require_engine_query(query)

    engine = _coerce_registered_engine(engine)

    # Check in-memory cache first (exact match, fast)
    cache = get_search_cache()
    key = cache_key(
        "deep_research",
        engine,
        str(max_sources),
        str(expand_queries),
        str(primary_sources_only),
        str(auto_fetch),
        query,
    )
    cached = cache.get(key)
    if cached is not None:
        logger.debug("Cache hit for deep_research: %s", query)
        return cached  # type: ignore[no-any-return]

    # Check persisted knowledge store for similar prior research (semantic match)
    try:
        from .harness.persistence import KnowledgeStore

        store = KnowledgeStore()
        prior = store.query(query, max_results=1, semantic_threshold=0.88)
        if prior:
            entry = prior[0]
            # Verify the prior research isn't too stale (> 24 hours for exact reuse)
            from datetime import datetime, timezone

            try:
                saved = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - saved).total_seconds() / 3600
                if age_hours < 24:
                    logger.info(
                        "KnowledgeStore hit for deep_research: %s (%.1fh old)", query, age_hours
                    )
                    capped = _cap_knowledge_answer(entry.answer)
                    cache.set(key, capped)
                    return capped
            except Exception:
                pass
    except Exception:
        pass  # Non-critical: fall through to live search

    deep_timeout = DEFAULT_CONFIG.deep_research_timeout_seconds
    try:
        result = await asyncio.wait_for(
            deep_research(
                query=query,
                engine=engine,
                max_sources=max_sources,
                expand_queries=expand_queries,
                primary_sources_only=primary_sources_only,
            ),
            timeout=deep_timeout,
        )
    except asyncio.TimeoutError:
        return (
            f"## [TIMEOUT] Deep research exceeded {deep_timeout:.0f} seconds.\n\n"
            "_The query may be too broad or search engines are responding slowly.\n"
            "Suggestions:\n"
            "- Reduce max_sources (e.g., 4 instead of 8)\n"
            "- Use web_search for faster results\n"
            "- Try a more specific query_"
        )
    planned = plan_reads(query, result.sources)
    research_packet = format_for_llm(result, planned_reads=planned)
    result_text = research_packet

    # Auto-fetch top results if requested (saves agent from separate fetch_page calls)
    if auto_fetch > 0 and result.sources:
        top_sources = result.sources[: min(auto_fetch, 3)]
        if planned:
            top_sources = [
                s
                for s in result.sources
                if s.citation_id in {p.citation_id for p in planned[: min(auto_fetch, 3)]}
            ] or result.sources[: min(auto_fetch, 3)]
        fetch_lines = ["\n### Auto-Fetched Content", ""]
        fetch_lines.extend(await _parallel_auto_fetch_previews(top_sources))
        result_text += "\n" + "\n".join(fetch_lines)

    report = analyze_content(result_text)
    result_text = wrap_serp_content(
        result_text, source_url="deep-research:multiple-sources", report=report
    )
    result_text += format_query_meta(prep)
    persisted = persist_research_artifacts(
        result=result,
        formatted_packet=research_packet,
        save_knowledge=False,
    )
    result_text = append_research_footer(result_text, persisted.research_id, persisted.receipt_path)
    save_research_knowledge(result, result_text)
    cache.set(key, result_text)
    return result_text


# ═══════════════════════════════════════════════════════════════
# Tool: answer (NEW — Perplexity-style direct answer)
# ═══════════════════════════════════════════════════════════════


def _answer_mode_config(mode: str) -> tuple[str, bool, int]:
    normalized = mode.strip().lower()
    if normalized == "fast":
        return "fast", False, 0
    if normalized == "deep":
        return "deep", True, 3
    return "balanced", True, 2


def _format_source_map(result_text: str) -> str:
    if not result_text.strip():
        return ""
    return "\n".join(
        [
            "### Research Packet",
            "",
            result_text,
        ]
    )


def _compact_fetch_preview(page: str, max_tokens: int) -> str:
    body = unwrap_external_content(page)
    return truncate_for_llm(body, max_tokens=max(250, min(max_tokens, 1800)))


async def tool_answer(
    query: str,
    engine: str = DEFAULT_CONFIG.default_engine,
    max_sources: int = DEFAULT_CONFIG.max_results_per_query,
    max_tokens: int = 8000,
    primary_sources_only: bool = False,
    mode: str = "balanced",
) -> str:
    """Return an answer-ready research packet for a general user question.

    No LLM synthesis happens inside the MCP server. Instead this gathers live
    sources, optionally reads the best pages, and returns a compact packet that
    the host agent can turn into a Perplexity-style answer with citations.

    BEST FOR:
    - Factual questions ("What is X?", "latest price?", "what changed?")
    - Consumer recommendations ("갤럭시 중고폰 최신 시세 추천 2026")
    - How-to and comparison questions

    NOT FOR:
    - Creative writing
    - Reading specific known URLs (use fetch_page)
    """
    query, prep = require_engine_query(query)
    mode, expand_queries, fetch_count = _answer_mode_config(mode)

    engine = _coerce_registered_engine(engine)
    source_limit = max(1, min(max_sources, 12))
    if mode == "fast":
        source_limit = min(source_limit, 6)

    answer_timeout = DEFAULT_CONFIG.answer_timeout_seconds
    try:
        result = await asyncio.wait_for(
            deep_research(
                query=query,
                engine=engine,
                max_sources=source_limit,
                expand_queries=expand_queries,
                primary_sources_only=primary_sources_only,
            ),
            timeout=answer_timeout,
        )
    except asyncio.TimeoutError:
        return (
            f"## [TIMEOUT] Answer generation exceeded {answer_timeout:.0f} seconds.\n\n"
            f"_Query: {query}_\n\n"
            "Try a more specific question or use web_search instead."
        )

    if not result.sources:
        return f"I couldn't find any sources for: **{query}**"

    planned = plan_reads(query, result.sources)
    research_packet = format_for_llm(result, planned_reads=planned)
    fetch_lines: list[str] = []
    fetched_count = 0
    if fetch_count:
        selected = [
            s
            for s in result.sources
            if s.citation_id in {p.citation_id for p in planned[:fetch_count]}
        ] or result.sources[:fetch_count]
        n_fetch = len(selected[:fetch_count])
        fetch_budget = max(50, max_tokens // max(n_fetch + 2, 3)) if n_fetch else 0
        if n_fetch and fetch_budget * n_fetch > max_tokens:
            fetch_budget = max(1, max_tokens // n_fetch)
        fetch_lines.extend(["### Fetched Evidence", ""])
        evidence, fetched_count = await _parallel_answer_evidence(
            selected[:fetch_count],
            fetch_budget=fetch_budget,
        )
        fetch_lines.extend(evidence)

    quality = answer_quality_suffix(result)
    lines = [
        f"## Answer Engine: {query}",
        f"_mode: {mode} | sources: {len(result.sources)} | fetched: {fetched_count} | "
        f"engine: {result.engine} | {quality}_",
        "",
        "### Host Synthesis Instructions",
        "Answer from evidence only; cite every factual claim with `[N]` IDs; note uncertainty or conflicts.",
        "",
        _format_source_map(research_packet),
    ]
    if fetch_lines:
        lines.extend(["", *fetch_lines])
    lines.append(format_query_meta(prep).strip())
    body = "\n".join(line for line in lines if line is not None)

    persisted = persist_research_artifacts(
        result=result,
        formatted_packet=research_packet,
        save_knowledge=False,
    )
    final = append_research_footer(body, persisted.research_id, persisted.receipt_path)
    save_research_knowledge(result, final)
    return final


# ═══════════════════════════════════════════════════════════════
# Tool: search_with_citations
# ═══════════════════════════════════════════════════════════════


async def tool_search_with_citations(
    query: str,
    engine: str = DEFAULT_CONFIG.default_engine,
    max_results: int = DEFAULT_CONFIG.max_results_per_query,
) -> str:
    """Search the web and return citation-ready results.

    Each result includes a citation ID [1], [2] that can be referenced
    in follow-up fetch_page or fetch_bulk calls.

    BEST FOR:
    - When you need to cite specific sources in your answer
    - Academic or technical writing with source attribution
    - Building a bibliography before deep reading
    """
    query, prep = require_engine_query(query)

    engine = _coerce_registered_engine(engine)

    serp_timeout = DEFAULT_CONFIG.serp_timeout_seconds
    try:
        search_engine = SearchEngineRegistry.create(engine)
        optimized_query = optimize_for_engine(query, engine)
        results = await asyncio.wait_for(
            search_engine.search(optimized_query, max_results=max_results),
            timeout=serp_timeout,
        )
    except asyncio.TimeoutError:
        return (
            f"## [TIMEOUT] Search for '{query}' exceeded {serp_timeout:.0f} seconds.\n\n"
            "_The search engine may be slow or blocked.\n"
            "Try a different engine or a more specific query._"
        )
    except MaruSearchError as e:
        if e.suggested_engine and e.suggested_engine != engine:
            search_engine = SearchEngineRegistry.create(e.suggested_engine)
            fb_query = optimize_for_engine(query, e.suggested_engine)
            try:
                results = await asyncio.wait_for(
                    search_engine.search(fb_query, max_results=max_results),
                    timeout=serp_timeout,
                )
            except asyncio.TimeoutError:
                return (
                    f"## [TIMEOUT] Search for '{query}' exceeded {serp_timeout:.0f} seconds "
                    f"(fallback engine {e.suggested_engine}).\n\n"
                    "_The search engine may be slow or blocked.\n"
                    "Try a different engine or a more specific query._"
                )
        else:
            raise

    if not results:
        return f"No results found for: {query}"

    # Assign citation IDs
    for i, r in enumerate(results, 1):
        r.citation_id = i

    lines = [f"## Citation Search: {query}\n"]
    for r in results:
        type_badge = (
            f" [{r.likely_content_type.value}]" if r.likely_content_type.value != "unknown" else ""
        )
        source_badge = ""
        if r.source_type and r.source_type.value != "unknown":
            source_badge = f" [{r.source_type.value.upper().replace('_', '-')}]"
        primary_badge = " [PRIMARY]" if r.is_primary else ""
        auth_badge = (
            " [AUTHORITY]"
            if any(
                d in r.domain
                for d in [
                    "docs.python.org",
                    "developer.mozilla.org",
                    "github.com",
                    "stackoverflow.com",
                    "arxiv.org",
                ]
            )
            else ""
        )
        lines.append(
            f"[{r.citation_id}] **{r.title}**{type_badge}{source_badge}{primary_badge}{auth_badge}"
        )
        lines.append(f"    URL: {r.url}")
        if r.snippet:
            lines.append(f"    > {r.snippet[:300]}")
        lines.append("")

    lines.append("---")
    lines.append("Use `fetch_page(url)` or `fetch_bulk(urls)` to read full content.")
    return "\n".join(lines) + format_query_meta(prep)


# ═══════════════════════════════════════════════════════════════
# Tool: stealthy_fetch
# ═══════════════════════════════════════════════════════════════


async def tool_stealthy_fetch(url: str, max_tokens: int = 6000) -> str:
    """Fetch a URL with full StealthyFetcher anti-bot bypass.

    Use Cases:
    - Sites behind Cloudflare Turnstile, DataDome, or PerimeterX
    - When fetch_page returns [BLOCKED] or incomplete content
    - High-value sources where access certainty matters

    Trade-offs:
    - Slower: ~3-5x slower than fetch_page due to browser automation
    - More resource intensive: Uses headless browser
    - May still fail on the most advanced protections

    Recommendation: Try fetch_page first, fall back to stealthy_fetch
    only if needed.
    """
    return await tool_fetch_page(
        url, stealth=True, max_tokens=max_tokens, auto_stealth_fallback=False
    )


# ═══════════════════════════════════════════════════════════════
# Tool: parallel_search
# ═══════════════════════════════════════════════════════════════


async def tool_parallel_search(
    queries: list[str],
    engine: str = DEFAULT_CONFIG.default_engine,
    max_results: int = DEFAULT_CONFIG.max_results_per_query,
    comparison_mode: bool = False,
) -> str:
    """Run multiple searches in parallel. Each query scrapes the search engine independently.

    comparison_mode: When True, attempts to organize results into a structured
        comparison table with source type classification and primary source badges.
    """
    gated: list[tuple[str, QueryPrepResult]] = [require_engine_query(q) for q in queries]
    queries = [g[0] for g in gated]
    query_meta = "".join(format_query_meta(p) for _, p in gated if format_query_meta(p))

    engine = _coerce_registered_engine(engine)

    _search_sem = asyncio.Semaphore(4)

    async def _search_one(q: str) -> str:
        async with _search_sem:
            try:
                return await tool_web_search(q, engine=engine, max_results=max_results)
            except Exception as exc:
                return f"**Search failed for '{q}':** {exc}"

    results = await asyncio.gather(*(_search_one(q) for q in queries))

    if not comparison_mode:
        return "\n\n---\n\n".join(results) + query_meta

    # ── Comparison mode: renumber and structure ──
    all_lines: list[str] = []
    all_lines.append("## Parallel Search Results")
    all_lines.append("")

    global_id = 1
    query_blocks: list[tuple[str, list[str]]] = []

    for q, raw in zip(queries, results, strict=False):
        block_lines: list[str] = []
        # Renumber citation IDs in this block
        id_map: dict[str, str] = {}
        for m in re.finditer(r"\[(\d+)\]", raw):
            old_id = m.group(1)
            if old_id not in id_map:
                id_map[old_id] = str(global_id)
                global_id += 1

        # Replace IDs — bind id_map via default arg to avoid closure issue
        def _repl_id(m, _mapping=id_map):
            return f"[{_mapping.get(m.group(1), m.group(1))}]"

        renumbered = re.sub(r"\[(\d+)\]", _repl_id, raw)

        # Add source type badges if missing
        block_lines.append(f"### Query: {q}")
        block_lines.extend(renumbered.split("\n"))
        query_blocks.append((q, block_lines))

    # Build comparison summary table
    all_lines.append("### Comparison Summary")
    all_lines.append("")
    all_lines.append("| Query | Top Source | Type | Primary |")
    all_lines.append("|-------|-----------|------|---------|")

    for q, block_lines in query_blocks:
        # Extract first source from block
        first_title = ""
        first_url = ""
        first_type = ""
        first_primary = ""
        for line in block_lines:
            # Skip header lines
            if "Search:" in line:
                continue
            # Title: lines like '1. **Title** [1] [type]'
            if not first_title and "**" in line:
                title_match = re.search(r"\*\*(.*?)\*\*", line)
                if title_match:
                    first_title = title_match.group(1).strip()[:40]
            # URL: indented lines
            if line.startswith("   http") and not first_url:
                first_url = line.strip()
            if "[OFFICIAL-DOCS]" in line or "[GITHUB-REPO]" in line:
                first_type = line[line.find("[") : line.find("]") + 1]
            if "[PRIMARY]" in line:
                first_primary = "✓"
        if not first_title and first_url:
            # Fallback to domain name
            from urllib.parse import urlparse

            first_title = urlparse(first_url).netloc[:40]
        if not first_title:
            first_title = "(no title)"
        all_lines.append(f"| {q[:30]} | {first_title} | {first_type} | {first_primary} |")

    all_lines.append("")
    all_lines.append("---")
    all_lines.append("")

    for _q, block_lines in query_blocks:
        all_lines.extend(block_lines)
        all_lines.append("")

    return "\n".join(all_lines) + query_meta


# ═══════════════════════════════════════════════════════════════
# Tool Guidance
# ═══════════════════════════════════════════════════════════════
