"""Atomic fetch tools with content refinement for the MCP server redesign.

Downloads web pages, extracts markdown, and uses the refiner engine to clean
content before returning to the host LLM — saving ~83% tokens vs raw HTML.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..config import DEFAULT_CONFIG
from ..engines.base import ExtractionQuality, PageContent
from ..engines.registry import SearchEngineRegistry
from ..extraction.content import estimate_token_count, truncate_for_llm
from ..utils.sanitize import analyze_content, wrap_external_content

logger = logging.getLogger(__name__)

# Lazy refiner import — graceful degradation if unavailable
try:
    from ..refiner.engine import RefinerEngine

    _REFINER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _REFINER_AVAILABLE = False
    RefinerEngine = None  # type: ignore[misc,assignment]
    logger.debug("RefinerEngine unavailable; fetch will use truncate_for_llm fallback")


def _get_refiner() -> Any | None:
    """Return a RefinerEngine instance, or None if unavailable."""
    if not _REFINER_AVAILABLE or RefinerEngine is None:
        return None
    try:
        return RefinerEngine()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialise RefinerEngine: %s", exc)
        return None


def _fetch_engine() -> Any:
    """Return the default fetch engine instance."""
    name = "duckduckgo_fetch"
    if name not in SearchEngineRegistry.list_engines():
        name = "duckduckgo_lite"
    return SearchEngineRegistry.create(name)


def _calculate_savings(original: str, refined: str) -> float:
    """Calculate token savings percentage.

    Args:
        original: Original content before refinement.
        refined: Content after refinement.

    Returns:
        Percentage of tokens saved (0.0–100.0).
    """
    orig_tokens = max(1, estimate_token_count(original))
    refined_tokens = estimate_token_count(refined)
    if orig_tokens <= 0:
        return 0.0
    saved = orig_tokens - refined_tokens
    return max(0.0, (saved / orig_tokens) * 100)


def _apply_security_wrap(content: str, url: str) -> str:
    """Add security wrapper to fetched content.

    Args:
        content: Raw or refined content to wrap.
        url: Source URL for metadata.

    Returns:
        Content wrapped with security boundaries and risk metadata.
    """
    report = analyze_content(content)
    return wrap_external_content(content, source_url=url, report=report)


async def _fetch_single(url: str, max_tokens: int, query: str = "") -> dict[str, Any]:
    """Fetch and refine content from a single URL.

    Args:
        url: URL to fetch.
        max_tokens: Maximum tokens for refined output.
        query: Optional query context for relevance filtering.

    Returns:
        Dictionary with keys: title, url, final_url, content, quality,
        content_type, access_risk, warnings, original_tokens,
        refined_tokens, savings_pct, error.
    """
    from ..utils.url import normalize_url

    norm_url = normalize_url(url)
    fetch_timeout = DEFAULT_CONFIG.http_fetch_timeout_seconds
    engine = _fetch_engine()

    result: dict[str, Any] = {
        "title": "",
        "url": norm_url,
        "final_url": "",
        "content": "",
        "quality": "low",
        "content_type": "unknown",
        "access_risk": "open",
        "warnings": [],
        "original_tokens": 0,
        "refined_tokens": 0,
        "savings_pct": 0.0,
        "error": None,
    }

    try:
        page: PageContent = await asyncio.wait_for(
            engine.fetch(url, stealth=False),
            timeout=fetch_timeout,
        )
    except asyncio.TimeoutError:
        result["error"] = f"Fetch timeout after {fetch_timeout:.0f} seconds"
        result["quality"] = "blocked"
        return result
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
        result["quality"] = "blocked"
        return result

    result["final_url"] = page.final_url or norm_url
    result["title"] = page.title or norm_url
    result["quality"] = page.quality.value
    result["content_type"] = page.content_type.value
    result["access_risk"] = page.access_risk

    if page.quality == ExtractionQuality.BLOCKED:
        result["error"] = page.error_message or "Fetch blocked"
        return result

    if page.content_length == 0:
        result["error"] = "No extractable content found"
        result["quality"] = "empty"
        return result

    raw_content = page.markdown if page.markdown else page.text
    result["original_tokens"] = estimate_token_count(raw_content)

    # Try refiner first, fall back to truncation
    refiner = _get_refiner()
    if refiner is not None:
        try:
            refined = await refiner.refine_content(
                text=raw_content,
                query=query,
                max_tokens=max_tokens,
            )
            if refined and refined.strip():
                result["content"] = refined
            else:
                result["content"] = truncate_for_llm(raw_content, max_tokens)
                result["warnings"].append("Refiner returned empty; used truncation fallback")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Refiner failed for %s: %s", norm_url, exc)
            result["content"] = truncate_for_llm(raw_content, max_tokens)
            result["warnings"].append(f"Refiner error: {exc}")
    else:
        result["content"] = truncate_for_llm(raw_content, max_tokens)
        result["warnings"].append("Refiner unavailable; used truncation fallback")

    result["refined_tokens"] = estimate_token_count(result["content"])
    result["savings_pct"] = _calculate_savings(raw_content, result["content"])

    # Collect access warnings
    if page.access_reasons:
        result["warnings"].extend(page.access_reasons)

    return result


def _format_fetch_result(result: dict[str, Any]) -> str:
    """Format a single fetch result into the standard markdown output.

    Args:
        result: Dictionary from _fetch_single.

    Returns:
        Formatted markdown string.
    """
    if result.get("error"):
        return (
            f"## [{result['quality'].upper()}] {result['url']}\n"
            f"URL: {result['final_url'] or result['url']}\n"
            f"_quality: {result['quality']} | type: {result['content_type']}"
            f" | access: {result['access_risk']}_\n\n"
            f"{result['error']}\n\n"
            f"---\n"
            f"_sources: [{result['url']}]_\n"
            f"_warnings: [{'; '.join(result['warnings']) or 'none'}]_"
        )

    quality = result["quality"]
    content_type = result["content_type"]
    access = result["access_risk"]
    title = result["title"]
    url = result["final_url"] or result["url"]
    content = result["content"]
    original = result["original_tokens"]
    refined = result["refined_tokens"]
    savings = result["savings_pct"]
    warnings = result["warnings"]

    lines = [
        f"## {title}",
        f"URL: {url}",
        f"_quality: {quality} | type: {content_type} | access: {access}_",
        "",
        content,
        "",
        "---",
        f"_sources: [{url}]_",
        f"_warnings: [{'; '.join(warnings) or 'none'}]_",
        f"_stats: {original} → {refined} tokens ({savings:.0f}% saved)_",
    ]

    return "\n".join(lines)


async def tool_fetch(url: str, max_tokens: int = 6000) -> str:
    """Fetch and refine web page content.

    Downloads the page, extracts markdown, and internally refines it
    to remove ads, navigation, and irrelevant content before returning.

    Args:
        url: URL to fetch.
        max_tokens: Maximum tokens for refined output.

    Returns:
        Refined markdown content with metadata.
    """
    result = await _fetch_single(url, max_tokens)
    formatted = _format_fetch_result(result)
    return _apply_security_wrap(formatted, result["url"])


async def tool_fetch_bulk(
    urls: list[str],
    max_concurrent: int = 5,
    max_tokens: int = 3000,
    query: str = "",
) -> str:
    """Fetch multiple URLs concurrently with refinement.

    Args:
        urls: List of URLs to fetch.
        max_concurrent: Maximum concurrent fetch operations.
        max_tokens: Maximum tokens per refined output.
        query: Optional query context for relevance filtering.

    Returns:
        Combined refined markdown content for all URLs.
    """
    if not urls:
        return "No URLs provided."

    sem = asyncio.Semaphore(max_concurrent)

    async def _fetch_with_sem(u: str) -> dict[str, Any]:
        async with sem:
            return await _fetch_single(u, max_tokens, query=query)

    results = await asyncio.gather(*(_fetch_with_sem(u) for u in urls), return_exceptions=True)

    # Unwrap exceptions into error results
    safe_results: list[dict[str, Any]] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            safe_results.append(
                {
                    "title": "",
                    "url": urls[i],
                    "final_url": "",
                    "content": "",
                    "quality": "blocked",
                    "content_type": "unknown",
                    "access_risk": "open",
                    "warnings": [str(r)],
                    "original_tokens": 0,
                    "refined_tokens": 0,
                    "savings_pct": 0.0,
                    "error": str(r),
                }
            )
        else:
            safe_results.append(r)  # type: ignore[arg-type]

    # Build combined output
    sections: list[str] = []
    total_original = 0
    total_refined = 0
    all_warnings: list[str] = []

    for result in safe_results:
        sections.append(_format_fetch_result(result))
        sections.append("")
        if not result.get("error"):
            total_original += result["original_tokens"]
            total_refined += result["refined_tokens"]
        all_warnings.extend(result["warnings"])

    if len(safe_results) > 1:
        total_savings = _calculate_savings(" " * (total_original * 4), " " * (total_refined * 4))
        sections.append("---")
        sections.append(
            f"_bulk stats: {total_original} → {total_refined} tokens ({total_savings:.0f}% saved)_"
        )

    combined = "\n".join(sections)
    return _apply_security_wrap(combined, f"bulk:{len(urls)} URLs")
