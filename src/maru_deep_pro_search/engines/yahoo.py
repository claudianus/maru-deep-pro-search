"""Yahoo Search engine implementation with direct HTML scraping."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from scrapling import AsyncFetcher

from ..exceptions import NetworkError, ParseError
from ..utils.retry import with_retry
from ..utils.url import get_domain, resolve_redirect, should_skip_url
from .base import ContentType, PageContent, SearchEngine, SearchResult, _first, _guess_content_type

logger = logging.getLogger(__name__)

_SERP_SELECTORS = {
    "containers": [".algo"],
    "title": ["h3 span", "h3", ".title"],
    "url": [".compTitle a", "a[href]"],
    "snippet": [".compText p", ".compText span", ".compText"],
}

_DOCS_DOMAINS = {
    "docs.python.org", "python.org", "developer.mozilla.org", "mdn.io",
    "react.dev", "nextjs.org", "nodejs.org", "deno.com",
    "go.dev", "pkg.go.dev", "doc.rust-lang.org", "docs.rs",
    "api.rubyonrails.org", "guides.rubyonrails.org",
    "learn.microsoft.com", "docs.microsoft.com",
    "postgresql.org/docs", "dev.mysql.com/doc",
    "kubernetes.io/docs", "helm.sh/docs", "terraform.io/docs",
    "fastapi.tiangolo.com", "flask.palletsprojects.com",
    "docs.djangoproject.com", "vuejs.org", "svelte.dev",
}


class YahooEngine(SearchEngine):
    """Yahoo Search engine with direct HTML scraping."""

    name = "yahoo"
    supports_stealth = False
    quality_tier = 2
    typical_latency_ms = 1200
    reliability_score = 0.85

    def __init__(self):
        self._fetcher = AsyncFetcher()

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Yahoo with retry and fallback selectors."""
        search_url = f"https://search.yahoo.com/search?p={quote_plus(query)}&n={max_results}"

        try:
            page = await with_retry(
                self._fetcher.get,
                search_url,
                max_attempts=3,
                retryable_exceptions=(Exception,),
            )
        except Exception as exc:
            logger.error("Yahoo SERP scrape failed: %s", exc)
            raise NetworkError(f"Failed to fetch Yahoo SERP: {exc}", retryable=True) from exc

        results: list[SearchResult] = []
        seen: set[str] = set()

        containers = []
        for sel in _SERP_SELECTORS["containers"]:
            containers = page.css(sel)
            if containers:
                break

        for el in containers[:max_results * 2]:
            title_el = _first(el, _SERP_SELECTORS["title"])
            url_el = _first(el, _SERP_SELECTORS["url"])
            snippet_el = _first(el, _SERP_SELECTORS["snippet"])

            # Yahoo h3 span contains the actual title text
            title = title_el.get_all_text().replace("\n", " ").strip() if title_el else ""
            href = url_el.attrib.get("href", "") if url_el else ""
            snippet = snippet_el.get_all_text().replace("\n", " ").strip() if snippet_el else ""

            href = resolve_redirect(href, search_url)
            if not href or not title:
                continue
            if should_skip_url(href):
                continue

            norm = href.rstrip("/")
            if norm in seen:
                continue
            seen.add(norm)

            domain = get_domain(href)
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
                )
            )
            if len(results) >= max_results:
                break

        if not results:
            raise ParseError(
                "No results found on Yahoo",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            )

        return results

    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch a page with content extraction."""
        from .registry import SearchEngineRegistry

        engine = SearchEngineRegistry.create("duckduckgo")
        return await engine.fetch(url, stealth=stealth, timeout=timeout)




