"""Baidu search engine implementation with direct HTML scraping."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from scrapling import AsyncFetcher

from ..exceptions import NetworkError, ParseError
from ..utils.retry import with_retry
from ..utils.url import get_domain, should_skip_url
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
    "containers": [".c-container"],
    "title": ["h3"],
    "url": ["h3 a"],
    "snippet": [".c-abstract", ".content-right_8Zs40", ".c-span9"],
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


class BaiduEngine(SearchEngine):
    """Baidu Search engine with direct HTML scraping.

    Baidu places the real destination URL in the ``mu`` attribute of
    each ``.c-container`` result element, while the visible ``<a>``
    href is an internal redirect (``baidu.com/link?url=…``).

    We filter out ``result-op`` containers (AI answers, ads, and
    recommendation widgets) and only keep organic ``result``
    containers with a valid external ``mu`` URL.
    """

    name = "baidu"
    supports_stealth = False
    quality_tier = 2
    typical_latency_ms = 1500
    reliability_score = 0.75

    def __init__(self):
        super().__init__()
        self._fetcher = AsyncFetcher()

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Baidu with retry and fallback selectors."""
        search_url = f"https://www.baidu.com/s?wd={quote_plus(query)}&rn=10"

        try:
            page = await with_retry(
                self._fetcher.get,
                search_url,
                max_attempts=3,
                retryable_exceptions=(Exception,),
            )
        except Exception as exc:
            logger.error("Baidu SERP scrape failed: %s", exc)
            raise NetworkError(f"Failed to fetch Baidu SERP: {exc}", retryable=True) from exc

        results: list[SearchResult] = []
        seen: set[str] = set()

        containers = []
        for sel in _SERP_SELECTORS["containers"]:
            containers = page.css(sel)
            if containers:
                break

        for el in containers[: max_results * 3]:
            cls = el.attrib.get("class", "")

            # Skip Baidu-operated containers (AI answers, ads, recommendations)
            if "result-op" in cls:
                continue

            title_el = _first(el, _SERP_SELECTORS["title"])
            url_el = _first(el, _SERP_SELECTORS["url"])
            snippet_el = _first(el, _SERP_SELECTORS["snippet"])

            title = _extract_text(title_el)
            snippet = _extract_text(snippet_el)

            # Baidu stores the real URL in the "mu" attribute
            href = el.attrib.get("mu", "")
            if not href and url_el is not None:
                href = url_el.attrib.get("href", "")

            if not href or not title:
                continue

            # Skip internal Baidu URLs even if they leaked through
            if _is_baidu_noise(href):
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
                "No results found on Baidu",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            )

        return results

    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch a page with content extraction."""
        from .registry import SearchEngineRegistry

        engine = SearchEngineRegistry.create("duckduckgo")
        return await engine.fetch(url, stealth=stealth, timeout=timeout)


def _extract_text(el) -> str:
    """Safely extract cleaned text from a scrapling element."""
    if el is None:
        return ""
    txt = el.get_all_text().replace("\n", " ").strip()
    # Baidu often inserts extra spaces around highlighted terms
    while "  " in txt:
        txt = txt.replace("  ", " ")
    return txt


def _is_baidu_noise(url: str) -> bool:
    """Return True for Baidu-internal or placeholder URLs."""
    lower = url.lower()
    return any(
        p in lower
        for p in [
            "nourl.ubs.baidu.com",
            "recommend_list.baidu.com",
            "/baidu.php",
            "//baike.baidu.com",
        ]
    )
