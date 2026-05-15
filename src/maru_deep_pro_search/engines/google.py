"""Google search engine implementation with session-based stealth."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from scrapling import StealthyFetcher
from scrapling.fetchers import AsyncStealthySession

from ..exceptions import BlockedError, NetworkError, ParseError
from ..utils.retry import with_retry
from ..utils.url import get_domain, resolve_canonical_url, resolve_redirect, should_skip_url
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
    "containers": ["div.tF2Cxc", "div.g", "div[data-hveid]", "div[data-ved]"],
    "title": ["h3"],
    "url": ["a[href^='/url?']", "a[href^='http']", "div.yuRUbf a", "a.zReHs"],
    "snippet": ["div.VwiC3b", "span.aCOpRe", "div.s"],
}


class GoogleEngine(SearchEngine):
    """Google search engine with session-based stealth.

    Uses AsyncStealthySession to reuse a single browser instance
    across requests. This preserves cookies and browsing context,
    which significantly reduces the chance of hitting Google's
    rate limits compared to launching a fresh browser every time.
    """

    name = "google"
    supports_stealth = True
    quality_tier = 3
    typical_latency_ms = 3000
    reliability_score = 0.75
    min_request_interval = 3.0

    def __init__(self) -> None:
        super().__init__()
        self._session: AsyncStealthySession | None = None
        self._session_started = False
        StealthyFetcher.configure(adaptive=True, adaptive_domain="google.com")
        import atexit

        atexit.register(self._sync_close_session)

    def _sync_close_session(self) -> None:
        """Synchronous cleanup for atexit — best-effort session close."""
        if self._session is not None and self._session_started:
            try:
                import asyncio

                asyncio.run(self._session.close())
            except Exception:
                pass

    async def _get_session(self) -> AsyncStealthySession:
        """Lazy-start a persistent stealth session."""
        if self._session is None:
            self._session = AsyncStealthySession(
                headless=True,
                real_chrome=True,
                network_idle=True,
                block_webrtc=True,
                hide_canvas=True,
                locale="en-US",
                timezone_id="America/New_York",
            )
        if not self._session_started:
            await self._session.start()
            self._session_started = True
        return self._session

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Google with session-based stealth."""
        search_url = (
            f"https://www.google.com/search?q={quote_plus(query)}&num={max_results * 2}&hl=en"
        )

        session = await self._get_session()

        try:
            page = await with_retry(
                session.fetch,
                search_url,
                max_attempts=2,
                retryable_exceptions=(Exception,),
            )
        except Exception as exc:
            logger.error("Google SERP scrape failed: %s", exc)
            await self._reset_session()
            raise NetworkError(
                f"Google blocked all requests: {exc}",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            ) from exc

        html_content = str(page.html_content) if hasattr(page, "html_content") else ""
        if any(
            indicator in html_content
            for indicator in [
                "unusual traffic",
                "captcha",
                "recaptcha",
                "Before you continue",
                "I'm not a robot",
            ]
        ):
            raise BlockedError(
                "Google returned CAPTCHA/anti-bot page.",
                suggested_engine="duckduckgo_lite",
            )

        results: list[SearchResult] = []
        seen: set[str] = set()

        containers = []
        for sel in _SERP_SELECTORS["containers"]:
            try:
                containers = page.css(sel, auto_save=True, adaptive=True)
            except Exception:
                containers = page.css(sel)
            if containers:
                logger.debug("Found %d Google containers with: %s", len(containers), sel)
                break

        if not containers:
            logger.warning("No Google result containers found.")
            raise ParseError(
                "No Google results found. DOM may have changed or request was blocked.",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            )

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
            if not href.startswith("http"):
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
                    source_type=source_type,
                    is_primary=is_primary,
                    domain=domain,
                    url_suggests_docs=any(d in domain for d in DOCS_DOMAINS),
                    engine=self.name,
                )
            )
            if len(results) >= max_results:
                break

        if not results:
            raise ParseError(
                "No results extracted from Google.",
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
                await self._session.close()
            except Exception as exc:
                logger.warning("Error stopping Google session: %s", exc)
        self._session = None
        self._session_started = False
