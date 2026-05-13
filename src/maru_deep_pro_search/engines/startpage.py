"""Startpage search engine implementation with session-based stealth."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from scrapling.fetchers import AsyncStealthySession

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
    "containers": [".result"],
    "title": [".result-title h2", ".wgl-title", ".result-title", "h2"],
    "url": [".result-title", ".result-link", "a[href]"],
    "snippet": [".description", "p.description", "p"],
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


class StartpageEngine(SearchEngine):
    """Startpage search engine with session-based stealth.

    Startpage returns Google-quality results through a privacy proxy.
    Requires JavaScript rendering. We use AsyncStealthySession to
    reuse the browser across requests, reducing overhead and
    maintaining cookie continuity.
    """

    name = "startpage"
    supports_stealth = True
    quality_tier = 2
    typical_latency_ms = 3000
    reliability_score = 0.85

    def __init__(self):
        super().__init__()
        self._session: AsyncStealthySession | None = None
        self._session_started = False

    async def _get_session(self) -> AsyncStealthySession:
        """Lazy-start a persistent stealth session."""
        if self._session is None:
            self._session = AsyncStealthySession(
                headless=True,
                network_idle=True,
            )
        if not self._session_started:
            await self._session.start()
            self._session_started = True
        return self._session

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Startpage with retry and fallback selectors."""
        search_url = f"https://www.startpage.com/sp/search?query={quote_plus(query)}"

        session = await self._get_session()

        try:
            page = await with_retry(
                session.fetch,
                search_url,
                max_attempts=2,
                retryable_exceptions=(Exception,),
            )
        except Exception as exc:
            logger.error("Startpage SERP scrape failed: %s", exc)
            await self._reset_session()
            raise NetworkError(
                f"Failed to fetch Startpage SERP: {exc}",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            ) from exc

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
                "No results found on Startpage",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            )

        return results

    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch a page with content extraction."""
        from .registry import SearchEngineRegistry

        engine = SearchEngineRegistry.create("duckduckgo")
        return await engine.fetch(url, stealth=stealth, timeout=timeout)

    async def _reset_session(self):
        """Reset the browser session if it becomes corrupted."""
        if self._session is not None and self._session_started:
            try:
                await self._session.stop()
            except Exception as exc:
                logger.warning("Error stopping Startpage session: %s", exc)
        self._session = None
        self._session_started = False
