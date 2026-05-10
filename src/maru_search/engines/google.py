"""Google search engine implementation (best-effort scraping)."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from scrapling import DynamicFetcher, StealthyFetcher

from .base import SearchEngine, SearchResult, PageContent, ContentType, ExtractionQuality
from ..exceptions import NetworkError, ParseError, BlockedError
from ..utils.url import get_domain, should_skip_url, resolve_redirect
from ..utils.retry import with_retry

logger = logging.getLogger(__name__)

# NOTE: Google aggressively blocks scrapers. These selectors are
# best-effort and may break at any time. Stealth mode is strongly
# recommended. SearXNG provides more reliable Google results.
_SERP_SELECTORS = {
    "containers": ["div.g", "div[data-hveid]", "div[data-ved]"],
    "title": ["h3"],
    "url": ["div.yuRUbf > a", "a[href^='http']"],
    "snippet": ["div.VwiC3b", "span.aCOpRe", "div.s"],
}

_DOCS_DOMAINS = {
    "developers.google.com", "cloud.google.com",
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


def _first(el, selectors: list[str]):
    for sel in selectors:
        results = el.css(sel)
        if results:
            return results[0]
    return None


def _guess_content_type(url: str, snippet: str = "") -> ContentType:
    lower = (url + " " + snippet).lower()
    if any(k in lower for k in ["github.com", "gitlab.com", "bitbucket.org"]):
        return ContentType.CODE
    if any(k in lower for k in ["stackoverflow.com", "stackexchange.com", "discourse", "forum"]):
        return ContentType.FORUM
    if any(k in lower for k in ["docs.", "/docs/", "documentation", "reference", "api.", "/api/"]):
        return ContentType.DOCUMENTATION
    if any(k in lower for k in ["medium.com", "dev.to", "blog.", "/blog/"]):
        return ContentType.ARTICLE
    return ContentType.UNKNOWN


class GoogleEngine(SearchEngine):
    """Google search engine — best-effort direct scraping.

    .. warning::
        Google employs aggressive anti-bot measures (reCAPTCHA,
        JavaScript challenges, rate limiting). This engine uses
        StealthyFetcher by default and falls back to SearXNG when
        blocked. For reliable Google results, use ``searxng`` instead.
    """

    name = "google"
    supports_stealth = True

    def __init__(self):
        self._fetcher = DynamicFetcher()
        self._stealth_fetcher = StealthyFetcher()

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Google with stealth fallback and anti-bot detection."""
        search_url = (
            f"https://www.google.com/search?q={quote_plus(query)}"
            f"&num={max_results * 2}&hl=en"
        )

        page = None
        last_error: Exception | None = None

        # Try stealth fetch first, then normal fetch
        for use_stealth in [True, False]:
            fetcher = self._stealth_fetcher if use_stealth else self._fetcher
            try:
                page = await with_retry(
                    fetcher.async_fetch,
                    search_url,
                    max_attempts=2,
                    retryable_exceptions=(Exception,),
                )
                break
            except Exception as exc:
                last_error = exc
                logger.warning("Google %s fetch failed: %s", "stealth" if use_stealth else "normal", exc)
                continue

        if page is None:
            raise NetworkError(
                f"Google blocked all requests. Last: {last_error}",
                retryable=True,
                suggested_engine="searxng",
            )

        # Anti-bot detection
        html_content = page.html_content if hasattr(page, "html_content") else ""
        if any(indicator in html_content for indicator in [
            "unusual traffic", "captcha", "recaptcha",
            "Before you continue", "I'm not a robot",
        ]):
            raise BlockedError(
                "Google returned CAPTCHA/anti-bot page.",
                retryable=True,
                suggested_engine="searxng",
            )

        results: list[SearchResult] = []
        seen: set[str] = set()

        containers = []
        for sel in _SERP_SELECTORS["containers"]:
            containers = page.css(sel)
            if containers:
                logger.debug("Found %d Google containers with: %s", len(containers), sel)
                break

        if not containers:
            logger.warning("No Google result containers found — page structure may have changed.")
            raise ParseError(
                "No Google results found. DOM structure may have changed or Google blocked the request.",
                retryable=True,
                suggested_engine="searxng",
            )

        for el in containers[:max_results * 2]:
            title_el = _first(el, _SERP_SELECTORS["title"])
            url_el = _first(el, _SERP_SELECTORS["url"])
            snippet_el = _first(el, _SERP_SELECTORS["snippet"])

            title = title_el.text.strip() if title_el else ""
            href = url_el.attrib.get("href", "") if url_el else ""
            snippet = snippet_el.text.strip() if snippet_el else ""

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
                "No results extracted from Google. Likely blocked or DOM changed.",
                retryable=True,
                suggested_engine="searxng",
            )

        return results

    async def fetch(self, url: str, stealth: bool = False) -> PageContent:
        """Fetch a page with content extraction."""
        from .duckduckgo import DuckDuckGoEngine

        engine = DuckDuckGoEngine()
        return await engine.fetch(url, stealth=stealth)
