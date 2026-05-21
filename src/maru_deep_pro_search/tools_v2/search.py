"""Atomic search tool with intelligent ranking and snippet refinement.

Searches the web using the engine registry, ranks results with BM25+
metadata scoring, and optionally refines snippets through a local LLM
before returning token-efficient markdown to the host.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..config import DEFAULT_CONFIG
from ..engines.base import SearchResult
from ..engines.registry import SearchEngineRegistry
from ..exceptions import NetworkError
from ..extraction.content import estimate_token_count
from ..research.ranker import RankedResult, merge_results
from ..utils.locale_harness import optimize_for_engine
from ..utils.url import is_authority_domain, normalize_url

logger = logging.getLogger(__name__)

# Module-level semaphore to limit concurrent search requests
_search_semaphore = asyncio.Semaphore(4)

# Lazy refiner import — graceful degradation if llama-cpp is unavailable
try:
    from ..refiner.engine import RefinerEngine

    _REFINER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _REFINER_AVAILABLE = False
    RefinerEngine = None  # type: ignore[misc,assignment]
    logger.debug("RefinerEngine unavailable; search will return raw snippets")


def _get_refiner() -> Any | None:
    """Return a RefinerEngine instance, or None if unavailable."""
    if not _REFINER_AVAILABLE or RefinerEngine is None:
        return None
    try:
        return RefinerEngine()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialise RefinerEngine: %s", exc)
        return None


async def _search_one(
    engine_name: str,
    query: str,
    max_results: int,
    allow_fallback: bool = True,
) -> tuple[str, list[SearchResult]]:
    """Execute a single search and return (engine_name, results).

    Handles per-engine timeouts and optional fallback when the engine
    reports a suggested alternative.
    """
    async with _search_semaphore:
        try:
            search_engine = SearchEngineRegistry.create(engine_name)
            optimized_query = optimize_for_engine(query, engine_name)
            results = await asyncio.wait_for(
                search_engine.search(optimized_query, max_results=max_results),
                timeout=DEFAULT_CONFIG.serp_timeout_seconds,
            )
            return engine_name, results
        except asyncio.TimeoutError:
            logger.warning(
                "Search '%s' on %s timed out after %.0fs",
                query[:40],
                engine_name,
                DEFAULT_CONFIG.serp_timeout_seconds,
            )
            return engine_name, []
        except NetworkError as exc:
            logger.warning("Search '%s' on %s failed: %s", query[:40], engine_name, exc)
            fallback = getattr(exc, "suggested_engine", None)
            if fallback and fallback != engine_name and allow_fallback:
                logger.info("Engine fallback: %s -> %s", engine_name, fallback)
                return await _search_one(fallback, query, max_results, allow_fallback=False)
            return engine_name, []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Search '%s' on %s failed: %s", query[:40], engine_name, exc)
            return engine_name, []


async def tool_search(
    query: str,
    engine: str = "auto",
    max_results: int = 10,
) -> str:
    """Search the web and return structured, token-efficient results.

    Uses the engine registry to perform searches, the research ranker to
    score and deduplicate results, and an optional local refiner to clean
    snippets before presenting them to the host LLM.

    Args:
        query: Search query string.
        engine: Engine name or ``"auto"`` to let the registry pick the best
            combination based on the query locale and intent.
        max_results: Maximum number of results to return.

    Returns:
        Token-efficient markdown with ranked search results.
    """
    if not query or not query.strip():
        return "Error: empty query."

    query = query.strip()

    # Determine engine(s) to query
    if engine == "auto":
        engine_names = SearchEngineRegistry.recommend_engines(query)
        if not engine_names:
            engine_names = [DEFAULT_CONFIG.default_engine]
    else:
        if not SearchEngineRegistry.is_registered(engine):
            engine_names = [DEFAULT_CONFIG.default_engine]
        else:
            engine_names = [engine]

    # Run searches in parallel
    search_tasks = [
        asyncio.create_task(_search_one(name, query, max_results)) for name in engine_names
    ]

    engine_results: dict[str, list[SearchResult]] = {}
    search_runs: list[tuple[str, list[SearchResult]]] = []

    all_results = await asyncio.gather(*search_tasks, return_exceptions=True)
    for res in all_results:
        if isinstance(res, BaseException):
            logger.warning("Search task failed: %s", res)
            continue
        eng_name, results = res
        engine_results.setdefault(eng_name, []).extend(results)
        search_runs.append((eng_name, results))

    if not any(engine_results.values()):
        return f"No results found for: {query}"

    # Rank and deduplicate
    ranked: list[RankedResult] = merge_results(
        engine_results,
        query=query,
        search_runs=search_runs,
    )

    if not ranked:
        return f"No results found for: {query}"

    # Normalise relevance scores to 0–1
    max_score = max((rr.final_score for rr in ranked), default=1.0)
    if max_score <= 0:
        max_score = 1.0

    # Refine snippets in batch
    refiner = _get_refiner()
    refined_snippets: dict[str, str] = {}
    if refiner is not None:
        for rr in ranked[:max_results]:
            try:
                refined = await refiner.refine_snippet(
                    text=rr.result.snippet or "",
                    query=query,
                )
                refined_snippets[normalize_url(rr.result.url)] = refined
            except Exception as exc:  # noqa: BLE001
                logger.debug("Snippet refinement failed for %s: %s", rr.result.url, exc)

    # Build output
    lines: list[str] = []
    used_engine = engine if engine != "auto" else ",".join(engine_names)
    total = len(ranked)
    has_more = total > max_results

    lines.append(f'Search: "{query}" | {total} results | engine: {used_engine}')
    lines.append("")

    for rr in ranked[:max_results]:
        sr = rr.result
        norm_url = normalize_url(sr.url)

        relevance = min(rr.final_score / max_score, 1.0)
        relevance = max(relevance, 0.0)

        primary_badge = "📌primary" if sr.is_primary else ""
        authority_badge = "🔒authority" if is_authority_domain(sr.url) else ""
        type_label = sr.likely_content_type.value

        can_fetch = "no" if sr.access_risk == "blocked_likely" else "yes"
        snippet_text = refined_snippets.get(norm_url, sr.snippet or "")
        tokens = estimate_token_count(snippet_text)

        badges = " ".join(b for b in [primary_badge, authority_badge] if b)
        title_line = f"[{rr.citation_id}] {sr.title} (relevance: {relevance:.2f})"
        if badges:
            title_line += f" {badges}"
        title_line += f" {type_label}"
        lines.append(title_line)

        lines.append(f"URL: {sr.url}")
        lines.append(
            f"_relevance: {relevance:.2f} | type: {type_label} | "
            f"primary: {sr.is_primary} | authority: {is_authority_domain(sr.url)} | "
            f"can_fetch: {can_fetch} | estimated_tokens: {tokens}_"
        )
        if snippet_text:
            lines.append(snippet_text)
        lines.append("")

    suggested = ""
    lines.append("---")
    lines.append(f"_has_more: {has_more} | _suggested: {suggested}_")

    return "\n".join(lines)
