"""Deep research pipeline: search SERPs → crawl pages → extract content → structure for LLM.

The intelligence lives in the host LLM (Claude). This module provides the
crawling primitives and structures raw content for efficient consumption.
Rich metadata (quality scores, content types, link maps) flows through every
layer so the host LLM can make informed orchestration decisions."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from ..engines.duckduckgo import (
    SearchResult,
    PageContent,
    ContentType,
    ExtractionQuality,
    scrape_serp,
    fetch_page,
    fetch_many,
)
from .extractor import (
    truncate_for_llm,
    skip_url,
    deduplicate_urls,
)


@dataclass
class Source:
    url: str
    title: str
    snippet: str = ""
    content: str = ""          # plain text
    markdown: str = ""         # LLM-optimized markdown
    content_length: int = 0
    fetch_ms: float = 0.0
    # Quality metadata for LLM orchestration
    quality: str = ""          # high/medium/low/empty/blocked
    content_type: str = ""     # article/docs/forum/code/spam/unknown
    internal_links: list[dict] = field(default_factory=list)
    external_links: list[dict] = field(default_factory=list)
    # Code-aware metadata for coding agent optimization
    code_languages: list[str] = field(default_factory=list)
    api_signatures: list[dict] = field(default_factory=list)
    code_to_text_ratio: float = 0.0
    published_date: str = ""
    freshness_days: int | None = None
    is_api_reference: bool = False
    is_tutorial: bool = False
    is_error_solution: bool = False


@dataclass
class ResearchResult:
    query: str
    engine: str
    total_sources: int
    sources: list[Source] = field(default_factory=list)
    elapsed_ms: float = 0.0
    # Aggregate quality signals
    high_quality_count: int = 0
    blocked_count: int = 0


async def deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 8,
    follow_links: bool = False,
    stealth: bool = False,
) -> ResearchResult:
    """End-to-end deep research pipeline.

    1. Scrape search engine SERP → get result URLs + snippets + content type hints
    2. Concurrently crawl each result page → extract LLM-ready content with quality scores
    3. Optionally follow external links from crawled pages (using engine-collected links)
    4. Structure into Source list with quality metadata for LLM consumption

    Args:
        query: Search query.
        engine: Search engine to scrape ("duckduckgo", "duckduckgo_lite", "google", "bing").
        max_sources: Max unique pages to crawl.
        follow_links: If True, follow one level of external links from crawled pages.
        stealth: Use full StealthyFetcher for anti-bot bypass on target pages.
    """
    t0 = time.monotonic()

    # ── Phase 1: Search ──────────────────────────────────
    serp_results = await scrape_serp(query, engine=engine, max_results=max_sources * 2)

    if not serp_results:
        return ResearchResult(query=query, engine=engine, total_sources=0)

    # Filter out non-content URLs, prioritize docs/known-good domains
    candidates = [r for r in serp_results if not skip_url(r.url)]
    # Sort: docs first, then articles, then unknown
    candidates.sort(key=lambda r: (
        0 if r.likely_content_type in (ContentType.DOCUMENTATION, ContentType.ARTICLE) else
        1 if r.likely_content_type == ContentType.CODE else
        2
    ))
    urls_to_fetch = [r.url for r in candidates[:max_sources] if r.url]
    urls_to_fetch = deduplicate_urls(urls_to_fetch)

    # ── Phase 2: Crawl pages concurrently ────────────────
    pages = await fetch_many(urls_to_fetch, stealth=stealth)

    # Build sources from SERP results + crawled content
    sources: list[Source] = []
    high_quality = 0
    blocked = 0

    for sr in candidates[:max_sources]:
        matched = next((p for p in pages if p.url == sr.url or p.final_url == sr.url), None)

        if matched and matched.quality == ExtractionQuality.BLOCKED:
            blocked += 1

        if matched and matched.content_length > 100:
            if matched.quality == ExtractionQuality.HIGH:
                high_quality += 1
            sources.append(Source(
                url=matched.final_url or matched.url,
                title=matched.title or sr.title,
                snippet=sr.snippet,
                content=matched.text,
                markdown=matched.markdown,
                content_length=matched.content_length,
                fetch_ms=matched.fetch_duration_ms,
                quality=matched.quality.value if matched.quality else "",
                content_type=matched.content_type.value if matched.content_type else "",
                internal_links=matched.internal_links,
                external_links=matched.external_links,
                code_languages=matched.code_languages,
                api_signatures=matched.api_signatures,
                code_to_text_ratio=matched.code_to_text_ratio,
                published_date=matched.published_date,
                freshness_days=matched.freshness_days,
                is_api_reference=matched.is_api_reference,
                is_tutorial=matched.is_tutorial,
                is_error_solution=matched.is_error_solution,
            ))
        elif sr.snippet:
            sources.append(Source(
                url=sr.url,
                title=sr.title,
                snippet=sr.snippet,
                quality="empty",
                content_type=sr.likely_content_type.value if sr.likely_content_type else "",
            ))

    # ── Phase 3: Follow links (optional) ─────────────────
    if follow_links and len(sources) < max_sources:
        fetched_urls = {s.url.rstrip("/") for s in sources}
        # Use engine-collected external links — no need to re-parse HTML
        all_external: list[str] = []
        for src in sources:
            for link in src.external_links:
                u = link.get("url", "")
                if u and not skip_url(u):
                    all_external.append(u)

        all_external = deduplicate_urls(all_external)
        new_urls = [u for u in all_external[:max_sources - len(sources)] if u.rstrip("/") not in fetched_urls]

        if new_urls:
            linked_pages = await fetch_many(new_urls, stealth=True)
            for lp in linked_pages:
                if lp.content_length > 200:
                    if lp.quality == ExtractionQuality.HIGH:
                        high_quality += 1
                    sources.append(Source(
                        url=lp.final_url or lp.url,
                        title=lp.title,
                        content=lp.text,
                        markdown=lp.markdown,
                        content_length=lp.content_length,
                        fetch_ms=lp.fetch_duration_ms,
                        quality=lp.quality.value if lp.quality else "",
                        content_type=lp.content_type.value if lp.content_type else "",
                        internal_links=lp.internal_links,
                        external_links=lp.external_links,
                        code_languages=lp.code_languages,
                        api_signatures=lp.api_signatures,
                        code_to_text_ratio=lp.code_to_text_ratio,
                        published_date=lp.published_date,
                        freshness_days=lp.freshness_days,
                        is_api_reference=lp.is_api_reference,
                        is_tutorial=lp.is_tutorial,
                        is_error_solution=lp.is_error_solution,
                    ))

    elapsed = (time.monotonic() - t0) * 1000
    return ResearchResult(
        query=query,
        engine=engine,
        total_sources=len(sources),
        sources=sources[:max_sources],
        elapsed_ms=elapsed,
        high_quality_count=high_quality,
        blocked_count=blocked,
    )


def format_for_llm(result: ResearchResult, max_tokens_per_source: int = 1500) -> str:
    """Format research results into token-efficient markdown for LLM consumption.

    Includes quality metadata so the host LLM can prioritize which sources to
    deep-read vs skim, and which links to pursue for follow-up research."""
    if not result.sources:
        return f"No results found for: '{result.query}' ({result.engine})"

    quality_summary = ""
    if result.high_quality_count or result.blocked_count:
        parts = []
        if result.high_quality_count:
            parts.append(f"{result.high_quality_count} high-quality")
        if result.blocked_count:
            parts.append(f"{result.blocked_count} blocked")
        quality_summary = f" | {' ,'.join(parts)}"

    lines = [
        f"## Research: {result.query}",
        f"_engine: {result.engine} | sources: {result.total_sources}{quality_summary} | {result.elapsed_ms:.0f}ms_\n",
    ]

    for i, src in enumerate(result.sources, 1):
        # Quality badge
        badge = ""
        if src.quality == "high":
            badge = " **[HIGH]**"
        elif src.quality == "medium":
            badge = " *[med]*"
        elif src.quality == "low":
            badge = " *[low]*"
        elif src.quality == "blocked":
            badge = " **[BLOCKED]**"

        type_hint = f" _({src.content_type})_" if src.content_type else ""

        # Code-aware badges for coding agent consumption
        code_badges: list[str] = []
        if src.is_api_reference:
            code_badges.append("[API-REF]")
        if src.is_tutorial:
            code_badges.append("[TUTORIAL]")
        if src.is_error_solution:
            code_badges.append("[ERROR-FIX]")
        if src.code_languages:
            code_badges.append(f"[{', '.join(src.code_languages[:3])}]")
        if src.code_to_text_ratio > 0.2:
            code_badges.append(f"[code-heavy {src.code_to_text_ratio:.0%}]")
        code_badge_str = " " + " ".join(code_badges) if code_badges else ""

        # Freshness warning for stale content
        freshness_warning = ""
        if src.freshness_days is not None and src.freshness_days > 365:
            freshness_warning = f" [STALE: {src.freshness_days // 30}mo old]"
        elif src.freshness_days is not None:
            freshness_warning = f" [{src.freshness_days}d ago]"
        elif src.published_date:
            freshness_warning = f" [{src.published_date}]"

        lines.append(f"### [{i}] {src.title}{badge}{type_hint}{code_badge_str}{freshness_warning}")
        lines.append(f"URL: {src.url}")

        # API signature preview for quick scanning
        if src.api_signatures:
            sig_preview = "; ".join(
                s["signature"][:80]
                for s in src.api_signatures[:6]
            )
            lines.append(f"_APIs: {sig_preview}_")

        # Surface link suggestions for LLM-guided follow-up
        if src.external_links:
            link_preview = ", ".join(
                f"[{l['text'][:40]}]({l['url']})"
                for l in src.external_links[:5]
            )
            lines.append(f"_Links: {link_preview}_")

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
