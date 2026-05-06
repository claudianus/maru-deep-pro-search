"""MCP tool definitions — all backed by Scrapling-native crawling.

Every tool response includes rich metadata (quality scores, content types,
link maps) so the host LLM can make informed decisions about which sources
to deep-read, which to skim, and what to pursue next."""

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

from .engines.duckduckgo import scrape_serp, fetch_page, fetch_many
from .research.deep import deep_research, format_for_llm
from .research.extractor import truncate_for_llm

SEARCH_ENGINES = ["duckduckgo", "duckduckgo_lite", "google", "bing"]


def _clean_urls(raw: str) -> list[str]:
    """Parse URLs from a string (newline-separated or JSON array)."""
    import json
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return [u.strip() for u in raw.split("\n") if u.strip() and u.startswith("http")]


# ═══════════════════════════════════════════════════════════════
# Tool: web_search
# Scrape a search engine SERP directly via Scrapling.
# ═══════════════════════════════════════════════════════════════

async def tool_web_search(
    query: str,
    engine: str = "duckduckgo_lite",
    max_results: int = 10,
) -> str:
    """Search by scraping a search engine's HTML results page directly.

    No API keys, no rate limits. Scrapling handles anti-bot bypass.
    Returns content type hints per result so the LLM can prioritize.
    """
    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

    results = await scrape_serp(query, engine=engine, max_results=max_results)

    if not results:
        return f"No results found for: {query}"

    lines = [f"Search: **{query}**  _engine={engine}_\n"]
    for r in results:
        type_badge = f" [{r.likely_content_type.value}]" if r.likely_content_type.value != "unknown" else ""
        lines.append(f"{r.position}. **{r.title}**{type_badge}")
        lines.append(f"   {r.url}")
        if r.snippet:
            lines.append(f"   > {r.snippet[:300]}")
        lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Tool: fetch_page
# Scrapling-fetch a URL and extract clean content for LLM.
# ═══════════════════════════════════════════════════════════════

async def tool_fetch_page(url: str, stealth: bool = False, max_tokens: int = 3000) -> str:
    """Fetch a page via Scrapling and extract LLM-optimized content.

    Strips nav, footer, ads, scripts. Returns structured markdown with
    quality signals, content type, and link suggestions for follow-up.
    """
    page = await fetch_page(url, stealth=stealth)

    if page.quality.value == "blocked":
        return (
            f"## [BLOCKED] {url}\n"
            f"_anti-bot wall hit, needs stealth upgrade_\n"
            f"Error: {page.error_message}"
        )

    if page.content_length == 0:
        return f"## [EMPTY] {url}\n_No extractable content found._"

    content = page.markdown if page.markdown else page.text
    content = truncate_for_llm(content, max_tokens)

    # Quality header
    quality_line = f"_quality: {page.quality.value} | type: {page.content_type.value} | {page.content_length} chars | {page.fetch_duration_ms:.0f}ms_"

    # Code-aware metadata for coding agent consumption
    code_meta = ""
    if page.code_languages:
        code_meta += f"\n_languages: {', '.join(page.code_languages)}_"
    if page.api_signatures:
        sigs = "; ".join(s["signature"][:80] for s in page.api_signatures[:5])
        code_meta += f"\n_API signatures: {sigs}_"
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

    # Link suggestions for LLM-guided follow-up
    link_section = ""
    if page.external_links:
        links_preview = "\n".join(
            f"- [{l['text'][:60]}]({l['url']})"
            for l in page.external_links[:5]
        )
        link_section = f"\n\n**Follow-up links:**\n{links_preview}"

    return (
        f"## {page.title}\n"
        f"URL: {page.final_url or url}\n"
        f"{quality_line}{code_meta}\n\n"
        f"{content}"
        f"{link_section}"
    )


# ═══════════════════════════════════════════════════════════════
# Tool: fetch_bulk
# Parallel Scrapling fetch of multiple URLs.
# ═══════════════════════════════════════════════════════════════

async def tool_fetch_bulk(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = 5,
    max_tokens: int = 1500,
) -> str:
    """Fetch multiple URLs in parallel via Scrapling.

    Each result includes quality signals so the LLM can prioritize reading.
    """
    pages = await fetch_many(urls, stealth=stealth, max_concurrent=max_concurrent)

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
        lines.append(f"### [{i}] {page.title}{badge}")
        lines.append(f"URL: {page.final_url or page.url} _({page.content_length} chars, {status}, {page.content_type.value})_")
        lines.append(f"\n{content}\n")

    return "\n".join(lines) if lines else "No content fetched."


# ═══════════════════════════════════════════════════════════════
# Tool: deep_research
# Full pipeline: search → crawl → extract → structure.
# ═══════════════════════════════════════════════════════════════

async def tool_deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 8,
    follow_links: bool = False,
) -> str:
    """End-to-end deep research pipeline.

    1. Scrape search engine SERP for result URLs
    2. Concurrently crawl each result page with Scrapling
    3. Extract clean, structured content (markdown when possible)
    4. Optionally follow external links from crawled pages
    5. Format into token-efficient markdown for LLM consumption

    Every source includes quality scores, content types, and link maps.
    The host LLM uses this metadata to decide which sources to deep-read,
    which to skim, and what to pursue for follow-up research.
    """
    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

    result = await deep_research(
        query=query,
        engine=engine,
        max_sources=max_sources,
        follow_links=follow_links,
        stealth=(engine == "google"),
    )
    return format_for_llm(result)


# ═══════════════════════════════════════════════════════════════
# Tool: stealthy_fetch
# Fetch with full anti-bot bypass (Cloudflare, DataDome, etc).
# ═══════════════════════════════════════════════════════════════

async def tool_stealthy_fetch(url: str, max_tokens: int = 3000) -> str:
    """Fetch a URL with full StealthyFetcher anti-bot bypass.

    Use for sites behind Cloudflare, DataDome, or other anti-bot protection.
    Automatically adapts browser fingerprint per site.
    """
    return await tool_fetch_page(url, stealth=True, max_tokens=max_tokens)


# ═══════════════════════════════════════════════════════════════
# Tool: parallel_search
# Run multiple searches in parallel across engines.
# ═══════════════════════════════════════════════════════════════

async def tool_parallel_search(
    queries: list[str],
    engine: str = "duckduckgo_lite",
    max_results: int = 5,
) -> str:
    """Run multiple searches in parallel. Each query scrapes the search engine independently."""
    if engine not in SEARCH_ENGINES:
        engine = "duckduckgo_lite"

    async def _search_one(q: str) -> str:
        return await tool_web_search(q, engine=engine, max_results=max_results)

    results = await asyncio.gather(*(_search_one(q) for q in queries))
    return "\n\n---\n\n".join(results)


# ═══════════════════════════════════════════════════════════════
# Tool registry
# ═══════════════════════════════════════════════════════════════

TOOLS = {
    "web_search": (tool_web_search, "Scrape a search engine results page directly via Scrapling. No API keys needed. Returns content type hints per result.", {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite",
                       "description": "Search engine to scrape. duckduckgo_lite is fastest."},
            "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    }),
    "fetch_page": (tool_fetch_page, "Fetch a URL via Scrapling and extract clean, LLM-optimized content with quality signals and follow-up links.", {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "stealth": {"type": "boolean", "default": False,
                        "description": "Use full anti-bot bypass for protected sites"},
            "max_tokens": {"type": "integer", "default": 3000, "minimum": 500, "maximum": 8000,
                           "description": "Approximate max output tokens"},
        },
        "required": ["url"],
    }),
    "fetch_bulk": (tool_fetch_bulk, "Fetch multiple URLs in parallel via Scrapling. Each result includes quality signals for LLM prioritization.", {
        "type": "object",
        "properties": {
            "urls": {"type": "array", "items": {"type": "string"},
                     "description": "List of URLs to fetch"},
            "stealth": {"type": "boolean", "default": False},
            "max_concurrent": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            "max_tokens": {"type": "integer", "default": 1500, "minimum": 300, "maximum": 5000},
        },
        "required": ["urls"],
    }),
    "deep_research": (tool_deep_research,
        "Full pipeline: scrape SERP → crawl pages → extract content → structure for LLM. Every source includes quality scores, content types, and link maps so the host LLM can intelligently decide what to deep-read, skim, or pursue next.", {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Research question or topic"},
            "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
            "max_sources": {"type": "integer", "default": 8, "minimum": 1, "maximum": 15},
            "follow_links": {"type": "boolean", "default": False,
                             "description": "Also crawl external links found on result pages"},
        },
        "required": ["query"],
    }),
    "stealthy_fetch": (tool_stealthy_fetch,
        "Fetch a URL with full anti-bot bypass (Cloudflare Turnstile, DataDome).", {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "max_tokens": {"type": "integer", "default": 3000, "minimum": 500, "maximum": 8000},
        },
        "required": ["url"],
    }),
    "parallel_search": (tool_parallel_search,
        "Run multiple searches in parallel, each scraping the search engine independently.", {
        "type": "object",
        "properties": {
            "queries": {"type": "array", "items": {"type": "string"},
                        "description": "Search queries to run in parallel"},
            "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["queries"],
    }),
}
