"""Ecosia search engine implementation with direct HTML scraping."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from scrapling import AsyncFetcher

from ..exceptions import NetworkError, ParseError
from ..utils.retry import with_retry
from ..utils.url import get_domain, should_skip_url
from .base import (
    DOCS_DOMAINS,
    PageContent,
    SearchEngine,
    SearchResult,
    _first,
    _guess_content_type,
    guess_source_type_and_primary,
)

logger = logging.getLogger(__name__)

_SERP_SELECTORS = {
    "containers": ["article.result"],
    "title": [".result-title__heading", ".result__title", "h2"],
    "url": ["a.result__link", "a[href^='http']"],
    "snippet": [".web-result__description", ".result__description", ".result__columns"],
}

class EcosiaEngine(SearchEngine):
    """Ecosia Search engine with direct HTML scraping."""

    name = "ecosia"
    supports_stealth = False
    quality_tier = 2
    typical_latency_ms = 1100
    reliability_score = 0.85
    min_request_interval = 1.0

    def __init__(self):
        super().__init__()
        self._fetcher = AsyncFetcher()

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Ecosia with retry and fallback selectors."""
        search_url = f"https://www.ecosia.org/search?q={quote_plus(query)}"

        try:
            page = await with_retry(
                self._fetcher.get,
                search_url,
                max_attempts=3,
                retryable_exceptions=(Exception,),
            )
        except Exception as exc:
            logger.error("Ecosia SERP scrape failed: %s", exc)
            raise NetworkError(f"Failed to fetch Ecosia SERP: {exc}", retryable=True) from exc

        results: list[SearchResult] = []
        seen: set[str] = set()

        containers = []
        for sel in _SERP_SELECTORS["containers"]:
            containers = page.css(sel)
            if containers:
                break

        for el in containers[: max_results * 2]:
            title_el = _first(el, _SERP_SELECTORS["title"])
            url_el = _first(el, _SERP_SELECTORS["url"])
            snippet_el = _first(el, _SERP_SELECTORS["snippet"])

            # Ecosia provides title in aria-label or inner heading
            title = ""
            if title_el:
                title = title_el.get_all_text().replace("\n", " ").strip()
            # Fallback to aria-label on the article container
            if not title:
                title = el.attrib.get("aria-label", "").strip()

            href = url_el.attrib.get("href", "") if url_el else ""
            snippet = snippet_el.get_all_text().replace("\n", " ").strip() if snippet_el else ""

            if not href or not title:
                continue
            if should_skip_url(href):
                continue

            norm = href.rstrip("/")
            if norm in seen:
                continue
            seen.add(norm)

            domain = get_domain(href)
            source_type, is_primary = guess_source_type_and_primary(href, snippet)
            results.append(
                SearchResult(
                    title=title,
                    url=href,
                    snippet=snippet,
                    position=len(results) + 1,
                    likely_content_type=_guess_content_type(href, snippet),
                    domain=domain,
                    url_suggests_docs=any(d in domain for d in DOCS_DOMAINS),
                    engine=self.name,
                    source_type=source_type,
                    is_primary=is_primary,
                )
            )
            if len(results) >= max_results:
                break

        if not results:
            raise ParseError(
                "No results found on Ecosia",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            )

        return results

    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch a page with content extraction."""
        from .registry import SearchEngineRegistry

        engine = SearchEngineRegistry.create("duckduckgo")
        return await engine.fetch(url, stealth=stealth, timeout=timeout)
