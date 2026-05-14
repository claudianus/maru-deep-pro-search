"""MCP tool definitions — universal AI search with Perplexity-level quality.

Every tool response includes rich metadata (quality scores, content types,
citations, link maps) so the host LLM can make informed decisions."""

from __future__ import annotations

import asyncio
import logging
import re

from .engines.registry import SearchEngineRegistry
from .exceptions import MaruSearchError
from .extraction.content import truncate_for_llm
from .research.deep import deep_research, format_for_llm
from .utils.cache import cache_key, get_fetch_cache, get_search_cache
from .utils.locale_harness import optimize_for_engine
from .utils.query_sanitize import sanitize_query
from .utils.retry import with_retry
from .utils.sanitize import analyze_content, wrap_external_content

logger = logging.getLogger(__name__)

# All registered engines
SEARCH_ENGINES = SearchEngineRegistry.list_engines()


# ═══════════════════════════════════════════════════════════════
# Tool: web_search
# ═══════════════════════════════════════════════════════════════


async def tool_web_search(
    query: str,
    engine: str = "duckduckgo_lite",
    max_results: int = 10,
) -> str:
    """Search by scraping a search engine's HTML results page directly.

    No API keys, no rate limits. Scrapling handles anti-bot bypass.
    Returns content type hints and citation IDs per result so the LLM
    can prioritize and cite sources.
    """
    query = sanitize_query(query)

    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

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
            with_retry(
                search_engine.search,
                optimized_query,
                max_results=max_results,
                max_attempts=3,
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        return (
            f"## [TIMEOUT] Search for '{query}' exceeded 30 seconds.\n\n"
            "_The search engine may be slow or blocked.\n"
            "Try a different engine or a more specific query._"
        )
    except MaruSearchError as e:
        if e.suggested_engine and e.suggested_engine != engine:
            logger.info("Falling back to %s", e.suggested_engine)
            search_engine = SearchEngineRegistry.create(e.suggested_engine)
            results = await search_engine.search(query, max_results=max_results)
        else:
            raise

    if not results:
        return f"No results found for: {query}"

    # Assign citation IDs
    for i, r in enumerate(results, 1):
        r.citation_id = i

    lines = [f"Search: **{query}**  _engine={engine}_\n"]
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
    result_text = wrap_external_content(result_text, source_url=f"search:{engine}", report=report)
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
    # Check cache
    cache = get_fetch_cache()
    key = cache_key("fetch", url, str(stealth))
    cached = cache.get(key)
    if cached is not None:
        logger.debug("Cache hit for fetch: %s", url)
        return cached  # type: ignore[no-any-return]

    engine = SearchEngineRegistry.create("duckduckgo")
    try:
        page = await asyncio.wait_for(
            engine.fetch(url, stealth=stealth),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        if auto_stealth_fallback and not stealth:
            logger.info("fetch_page timeout for %s, auto-falling back to stealthy_fetch", url)
            return await tool_stealthy_fetch(url, max_tokens)
        return (
            f"## [TIMEOUT] {url}\n"
            "_Fetch exceeded 20 seconds. The site may be too slow or blocked.\n"
            "Try stealthy_fetch() or a different URL._"
        )

    if page.quality.value == "blocked":
        err = page.error_message or ""
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
        if auto_stealth_fallback and not stealth:
            logger.info("fetch_page blocked for %s, auto-falling back to stealthy_fetch", url)
            return await tool_stealthy_fetch(url, max_tokens)
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
    cache.set(key, result_text)
    return result_text


# ═══════════════════════════════════════════════════════════════
# Tool: fetch_bulk
# ═══════════════════════════════════════════════════════════════


async def tool_fetch_bulk(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = 5,
    max_tokens: int = 3000,
) -> str:
    """Fetch multiple URLs in parallel via Scrapling.

    Each result includes quality signals so the LLM can prioritize reading.
    """
    engine = SearchEngineRegistry.create("duckduckgo")
    sem = asyncio.Semaphore(max_concurrent)

    async def _fetch_one(u: str):
        async with sem:
            try:
                return await asyncio.wait_for(
                    engine.fetch(u, stealth=stealth),
                    timeout=20.0,
                )
            except asyncio.TimeoutError:
                from .engines.base import ExtractionQuality, PageContent

                return PageContent(
                    url=u,
                    error_message="Fetch timeout after 20 seconds",
                    quality=ExtractionQuality.BLOCKED,
                    fetch_duration_ms=20000,
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
    pages = safe_pages

    lines: list[str] = []
    for i, page in enumerate(pages, 1):
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
    engine: str = "duckduckgo_lite",
    max_sources: int = 30,
    expand_queries: bool = True,
    primary_sources_only: bool = False,
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
    query = sanitize_query(query)

    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

    # Check cache
    cache = get_search_cache()
    key = cache_key(
        "deep_research",
        engine,
        str(max_sources),
        str(expand_queries),
        str(primary_sources_only),
        query,
    )
    cached = cache.get(key)
    if cached is not None:
        logger.debug("Cache hit for deep_research: %s", query)
        return cached  # type: ignore[no-any-return]

    try:
        result = await asyncio.wait_for(
            deep_research(
                query=query,
                engine=engine,
                max_sources=max_sources,
                expand_queries=expand_queries,
                primary_sources_only=primary_sources_only,
            ),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        return (
            "## [TIMEOUT] Deep research exceeded 45 seconds.\n\n"
            "_The query may be too broad or search engines are responding slowly.\n"
            "Suggestions:\n"
            "- Reduce max_sources (e.g., 4 instead of 8)\n"
            "- Use web_search for faster results\n"
            "- Try a more specific query_"
        )
    result_text = format_for_llm(result)
    report = analyze_content(result_text)
    result_text = wrap_external_content(
        result_text, source_url="deep-research:multiple-sources", report=report
    )
    cache.set(key, result_text)
    return result_text


# ═══════════════════════════════════════════════════════════════
# Tool: answer (NEW — Perplexity-style direct answer)
# ═══════════════════════════════════════════════════════════════


async def tool_answer(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 10,
    max_tokens: int = 8000,
    primary_sources_only: bool = False,
) -> str:
    """Get a direct, citation-backed answer to a question.

    Like Perplexity: searches the web, extracts top sources,
    and synthesizes a concise answer with inline citations [1], [2].

    BEST FOR:
    - Factual questions ("What is X?")
    - How-to questions ("How do I do Y?")
    - Comparison questions ("X vs Y?")

    NOT FOR:
    - Creative writing
    - Reading specific known URLs (use fetch_page)
    """
    query = sanitize_query(query)

    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

    try:
        result = await asyncio.wait_for(
            deep_research(
                query=query,
                engine=engine,
                max_sources=max_sources,
                expand_queries=True,
                primary_sources_only=primary_sources_only,
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        return (
            f"## [TIMEOUT] Answer generation exceeded 30 seconds.\n\n"
            f"_Query: {query}_\n\n"
            "Try a more specific question or use web_search instead."
        )

    if not result.sources:
        return f"I couldn't find any sources for: **{query}**"

    return format_for_llm(result)


# ═══════════════════════════════════════════════════════════════
# Tool: search_with_citations
# ═══════════════════════════════════════════════════════════════


async def tool_search_with_citations(
    query: str,
    engine: str = "duckduckgo_lite",
    max_results: int = 10,
) -> str:
    """Search the web and return citation-ready results.

    Each result includes a citation ID [1], [2] that can be referenced
    in follow-up fetch_page or fetch_bulk calls.

    BEST FOR:
    - When you need to cite specific sources in your answer
    - Academic or technical writing with source attribution
    - Building a bibliography before deep reading
    """
    query = sanitize_query(query)

    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

    try:
        search_engine = SearchEngineRegistry.create(engine)
        results = await asyncio.wait_for(
            with_retry(
                search_engine.search,
                query,
                max_results=max_results,
                max_attempts=3,
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        return (
            f"## [TIMEOUT] Search for '{query}' exceeded 30 seconds.\n\n"
            "_The search engine may be slow or blocked.\n"
            "Try a different engine or a more specific query._"
        )
    except MaruSearchError as e:
        if e.suggested_engine and e.suggested_engine != engine:
            search_engine = SearchEngineRegistry.create(e.suggested_engine)
            results = await search_engine.search(query, max_results=max_results)
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
    return "\n".join(lines)


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
    engine: str = "duckduckgo_lite",
    max_results: int = 5,
    comparison_mode: bool = False,
) -> str:
    """Run multiple searches in parallel. Each query scrapes the search engine independently.

    comparison_mode: When True, attempts to organize results into a structured
        comparison table with source type classification and primary source badges.
    """
    queries = [sanitize_query(q) for q in queries]

    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

    _search_sem = asyncio.Semaphore(4)

    async def _search_one(q: str) -> str:
        async with _search_sem:
            try:
                return await tool_web_search(q, engine=engine, max_results=max_results)
            except Exception as exc:
                return f"**Search failed for '{q}':** {exc}"

    results = await asyncio.gather(*(_search_one(q) for q in queries))

    if not comparison_mode:
        return "\n\n---\n\n".join(results)

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

    return "\n".join(all_lines)


# ═══════════════════════════════════════════════════════════════
# Tool Guidance
# ═══════════════════════════════════════════════════════════════

TOOL_GUIDANCE = """
## 🔴 Tool Selection Guide — ALWAYS RESEARCH BEFORE CODING

**Your training data is outdated. You MUST verify everything before acting.**

### The Golden Rule
```
EVERY technical request → deep_research(query) → THEN code
```

No exceptions. Not for "simple" questions. Not for things you "already know".
Libraries change. APIs break. New vulnerabilities are found daily.

### Why You Must Research First
| Scenario | Without Research | With Research |
|----------|-----------------|---------------|
| "Build a React app" | Uses React 18 patterns (outdated) | Uses React 19 / Next.js 15 patterns |
| "Is Express secure?" | Says "yes" from memory | Checks latest CVE-2024-XXXX |
| "Best Python web framework" | Recommends Flask (2010) | Recommends FastAPI (current) |
| "How to do auth" | Suggests JWT (vulnerable) | Suggests latest OAuth 2.1 / PKCE |

### Decision Tree & Tool Priority (ALWAYS follow this order)

#### 1. deep_research ⭐ MANDATORY FIRST STEP
**Use for**: LITERALLY EVERY technical request.
**What it does**: Expands query → searches 7 engines → crawls → BM25 ranks → synthesizes cited answer.
**Why first**: It searches the LIVE web, not your stale training data.

#### 2. answer
**Use for**: Quick factual verification AFTER deep_research.
**Still searches the web**, but faster and more focused.

#### 3. parallel_search
**Use for**: Multiple angles simultaneously.
**Example**: `["topic tutorial 2025", "topic best practices", "topic CVE"]`

#### 4. web_search / search_with_citations
**Use for**: Additional source gathering beyond deep_research results.

#### 5. fetch_page / fetch_bulk
**Use for**: Reading specific URLs found during research.

#### 6. stealthy_fetch
**Use for**: Blocked sites only. Last resort.

### Research Checklist (MANDATORY)
Before writing ANY code:
- [ ] Called `deep_research` on the user's topic
- [ ] Verified library/framework versions are current
- [ ] Checked for known security vulnerabilities
- [ ] Confirmed API signatures match latest documentation
- [ ] All claims backed by citations [1], [2]

### Performance Tips & Common Mistakes (CRITICAL)
- ❌ **SKIPPING RESEARCH** — Writing code from training data (MOST SEVERE)
- ❌ "I'll use X because I know it" — Your knowledge is 1-2 years old
- ❌ "This is simple, I don't need to search" — Simple things change too
- ❌ Using stealthy_fetch for every URL
- ❌ Not checking quality badges ([HIGH], [BLOCKED])
- ❌ Not citing sources
"""

# ═══════════════════════════════════════════════════════════════
# Tool registry with enhanced descriptions
# ═══════════════════════════════════════════════════════════════

TOOLS = {
    "answer": (
        tool_answer,
        "[POST-RESEARCH] BEST FOR: Quick factual verification AFTER deep_research. "
        "Get a direct, citation-backed answer to any question. "
        "Returns synthesized answer with inline citations [1], [2] like Perplexity. "
        "NOT FOR: Skipping deep_research on complex topics.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Question or topic to answer"},
                "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
                "max_sources": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30},
                "max_tokens": {
                    "type": "integer",
                    "default": 8000,
                    "minimum": 1000,
                    "maximum": 15000,
                },
                "primary_sources_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only official docs, GitHub, registries, papers, SO",
                },
            },
            "required": ["query"],
        },
    ),
    "web_search": (
        tool_web_search,
        "[SUPPLEMENTAL] BEST FOR: Additional targeted source gathering AFTER deep_research. "
        "Search the web by scraping search engine results. "
        "Use AFTER deep_research for additional targeted sources. "
        "Returns ranked results with [AUTHORITY] badges and citation IDs.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
                "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
    ),
    "search_with_citations": (
        tool_search_with_citations,
        "Search the web and return citation-ready results with IDs [1], [2]. "
        "BEST FOR: Academic writing, technical documentation, any task requiring source attribution. "
        "Each result includes a citation ID for referencing in answers.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
                "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
    ),
    "fetch_page": (
        tool_fetch_page,
        "Extract clean, readable content from a single URL. "
        "BEST FOR: Reading one specific page quickly. "
        "TRY FIRST before stealthy_fetch. "
        "If blocked, retry with stealth=True or use stealthy_fetch.",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "stealth": {
                    "type": "boolean",
                    "default": False,
                    "description": "Use anti-bot bypass. Try this if first attempt is blocked.",
                },
                "max_tokens": {"type": "integer", "default": 6000, "minimum": 500, "maximum": 8000},
            },
            "required": ["url"],
        },
    ),
    "fetch_bulk": (
        tool_fetch_bulk,
        "Fetch multiple URLs in parallel. "
        "BEST FOR: Reading 2-10 known URLs simultaneously. "
        "Each result includes quality signals ([HIGH], [BLOCKED]) for prioritization.",
        {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to fetch",
                },
                "stealth": {"type": "boolean", "default": False},
                "max_concurrent": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                "max_tokens": {"type": "integer", "default": 3000, "minimum": 300, "maximum": 5000},
            },
            "required": ["urls"],
        },
    ),
    "deep_research": (
        tool_deep_research,
        "🔴 MANDATORY FIRST STEP for ALL technical requests. "
        "BEST FOR: Exploring topics you don't know well, verifying current best practices, researching before coding. "
        "Searches 7 engines live → BM25 ranks → crawls → synthesizes cited answer. "
        "Use BEFORE writing code, proposing architecture, or making technical claims. "
        "Your training data is outdated. This tool searches the LIVE web. "
        "Deep multi-engine search with query expansion and intelligent ranking. "
        "Returns ranked URLs with rich metadata (authority, cross-engine confirmation, source type). "
        "The agent should review sources and call fetch_page / fetch_bulk to read relevant URLs. "
        "Use primary_sources_only=True for citation-grade official sources only. "
        "NOT FOR: When you already have specific URLs to read (use fetch_page instead).",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Research question or topic"},
                "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
                "max_sources": {"type": "integer", "default": 30, "minimum": 1, "maximum": 50},
                "expand_queries": {"type": "boolean", "default": True},
                "primary_sources_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only official docs, GitHub, registries, papers, SO",
                },
            },
            "required": ["query"],
        },
    ),
    "stealthy_fetch": (
        tool_stealthy_fetch,
        "Fetch a URL with full anti-bot bypass. "
        "BEST FOR: Sites that block regular fetching (Cloudflare, DataDome). "
        "USE AS LAST RESORT: Try fetch_page first, then fetch_page with stealth=True, then this. "
        "~3-5x slower than fetch_page but more reliable for protected sites.",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_tokens": {"type": "integer", "default": 6000, "minimum": 500, "maximum": 8000},
            },
            "required": ["url"],
        },
    ),
    "parallel_search": (
        tool_parallel_search,
        "Run multiple searches in parallel. "
        "BEST FOR: Getting multiple perspectives fast or comparing topics. "
        "Faster than calling web_search multiple times sequentially. "
        "Use comparison_mode=True to generate a structured comparison table.",
        {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Search queries to run in parallel",
                },
                "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                "comparison_mode": {
                    "type": "boolean",
                    "default": False,
                    "description": "Generate structured comparison table with renumbered citations",
                },
            },
            "required": ["queries"],
        },
    ),
}
