"""Bing search engine implementation."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from scrapling import AsyncFetcher

from ..exceptions import NetworkError, ParseError
from ..utils.retry import with_retry
from ..utils.url import get_domain, resolve_canonical_url, resolve_redirect, should_skip_url
from .base import (
    PageContent,
    SearchEngine,
    SearchResult,
    _first,
    _guess_content_type,
    guess_source_type_and_primary,
)

logger = logging.getLogger(__name__)

_SERP_SELECTORS = {
    "containers": ["li.b_algo", ".b_algo"],
    "title": ["h2 a", "h2", ".b_title"],
    "url": ["h2 a", "a[href]", ".b_attribution"],
    "snippet": [".b_caption p", ".b_snippet", ".b_paractl p", "p"],
}

_DOCS_DOMAINS = {
    "docs.python.org",
    "python.org",
    "developer.mozilla.org",
    "mdn.io",
    "react.dev",
    "nextjs.org",
    "nodejs.org",
    "deno.com",
    "go.dev",
    "pkg.go.dev",
    "doc.rust-lang.org",
    "docs.rs",
    "api.rubyonrails.org",
    "guides.rubyonrails.org",
    "learn.microsoft.com",
    "docs.microsoft.com",
    "postgresql.org/docs",
    "dev.mysql.com/doc",
    "kubernetes.io/docs",
    "helm.sh/docs",
    "terraform.io/docs",
    "fastapi.tiangolo.com",
    "flask.palletsprojects.com",
    "docs.djangoproject.com",
    "vuejs.org",
    "svelte.dev",
}


class BingEngine(SearchEngine):
    """Bing search engine with direct HTML scraping."""

    name = "bing"
    supports_stealth = True
    quality_tier = 2
    typical_latency_ms = 1200
    reliability_score = 0.90

    def __init__(self):
        super().__init__()
        self._fetcher = AsyncFetcher()

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Bing with retry and fallback selectors."""
        search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}&setmkt=en-US&setlang=en"

        try:
            page = await with_retry(
                self._fetcher.get,
                search_url,
                max_attempts=3,
                retryable_exceptions=(Exception,),
            )
        except Exception as exc:
            logger.error("Bing SERP scrape failed: %s", exc)
            raise NetworkError(f"Failed to fetch Bing SERP: {exc}", retryable=True) from exc

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

            # get_all_text() handles nested tags (<strong> inside <a> etc.)
            title = title_el.get_all_text().replace("\n", " ").strip() if title_el else ""
            href = url_el.attrib.get("href", "") if url_el else ""
            snippet = snippet_el.get_all_text().replace("\n", " ").strip() if snippet_el else ""

            href = resolve_redirect(href, search_url)
            href = resolve_canonical_url(href)
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
                    url_suggests_docs=any(d in domain for d in _DOCS_DOMAINS),
                    engine=self.name,
                    source_type=source_type,
                    is_primary=is_primary,
                )
            )
            if len(results) >= max_results:
                break

        if not results:
            raise ParseError(
                "No results found on Bing", retryable=True, suggested_engine="duckduckgo_lite"
            )

        return results

    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch a page with content extraction."""
        from .registry import SearchEngineRegistry

        engine = SearchEngineRegistry.create("duckduckgo")
        return await engine.fetch(url, stealth=stealth, timeout=timeout)
