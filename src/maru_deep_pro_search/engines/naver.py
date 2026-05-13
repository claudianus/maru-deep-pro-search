"""Naver search engine implementation for Korean queries."""

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
    _guess_content_type,
    _text,
    guess_source_type_and_primary,
)

logger = logging.getLogger(__name__)

# Naver SERP uses a component-based DOM (sds-comps / fds-web) that is SSR-friendly.
# Each result is wrapped in .fds-web-doc-root, with direct <a nocr="1"> links.
_SERP_CONTAINER = ".fds-web-doc-root"
_SERP_LINK = 'a[nocr="1"]'
_SERP_SITE_NAME = ".sds-comps-profile-info-title-text"

_UI_NOISE = {
    "Keep에 저장",
    "Keep에 바로가기",
    "새창열기",
    "더보기",
    "펼쳐보기",
    "모아보기",
    "관련문서 더보기",
    "원본보기",
}

_KOREAN_DOMAINS = {
    "velog.io",
    "tistory.com",
    "naver.com",
    "blog.naver.com",
    "brunch.co.kr",
    "okky.kr",
    "hashnode.dev",
    "dev.to",
    "inflearn.com",
    "programmers.co.kr",
    "codeit.kr",
    "nomadcoders.co",
    "fastcampus.co.kr",
    "spartacodingclub.kr",
}


class NaverEngine(SearchEngine):
    """Naver search engine for Korean-language search.

    Naver redesigned its SERP with obfuscated component classes
    (``sds-comps-*``, ``fender-ui_*``) but still SSRs the core
    result structure.  We target ``.fds-web-doc-root`` containers
    which reliably wrap each organic web result and contain a
    direct external ``<a nocr="1">`` link—no redirect decoding
    required.
    """

    name = "naver"
    supports_stealth = True
    quality_tier = 2
    typical_latency_ms = 1200
    reliability_score = 0.6

    def __init__(self):
        super().__init__()
        self._fetcher = AsyncFetcher()

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Naver with Korean query support."""
        search_url = f"https://search.naver.com/search.naver?query={quote_plus(query)}&where=web"

        try:
            page = await with_retry(
                self._fetcher.get,
                search_url,
                max_attempts=3,
                retryable_exceptions=(Exception,),
            )
        except Exception as exc:
            logger.error("Naver SERP scrape failed: %s", exc)
            raise NetworkError(f"Failed to fetch Naver SERP: {exc}", retryable=True) from exc

        docs = page.css(_SERP_CONTAINER)
        if not docs:
            raise ParseError(
                "No results found on Naver",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            )

        results: list[SearchResult] = []
        seen: set[str] = set()

        for doc in docs:
            if len(results) >= max_results:
                break

            result = _parse_doc(doc)
            if not result:
                continue

            if should_skip_url(result.url):
                continue

            norm = result.url.rstrip("/")
            if norm in seen:
                continue
            seen.add(norm)

            domain = get_domain(result.url)
            source_type, is_primary = guess_source_type_and_primary(result.url, result.snippet)
            results.append(
                SearchResult(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    position=len(results) + 1,
                    likely_content_type=_guess_content_type(result.url, result.snippet),
                    domain=domain,
                    url_suggests_docs=any(d in domain for d in _KOREAN_DOMAINS),
                    engine=self.name,
                    source_type=source_type,
                    is_primary=is_primary,
                )
            )

        if not results:
            raise ParseError(
                "No valid results extracted from Naver",
                retryable=True,
                suggested_engine="duckduckgo_lite",
            )

        return results

    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch a page with content extraction."""
        from .registry import SearchEngineRegistry

        engine = SearchEngineRegistry.create("duckduckgo")
        return await engine.fetch(url, stealth=stealth, timeout=timeout)


def _parse_doc(doc) -> _ParsedResult | None:
    """Extract title, url, snippet from a single ``.fds-web-doc-root``."""
    # --- URL ---
    link_els = doc.css(_SERP_LINK)
    if not link_els:
        return None
    href = link_els[0].attrib.get("href", "")
    if not href or not href.startswith("http"):
        return None

    # --- Site name ---
    site_name = ""
    site_els = doc.css(_SERP_SITE_NAME)
    if site_els:
        site_name = _text(site_els[0])
    if not site_name and link_els:
        # Fallback to first line of link text
        link_text = link_els[0].get_all_text().strip()
        if link_text:
            site_name = link_text.split("\n")[0].strip()

    # --- Full text parsing for title & snippet ---
    full_text = doc.get_all_text()
    lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]

    # Remove UI noise
    lines = [ln for ln in lines if ln not in _UI_NOISE]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for ln in lines:
        if ln in seen:
            continue
        seen.add(ln)
        unique.append(ln)

    # Filter breadcrumb / URL fragments
    cleaned: list[str] = []
    for ln in unique:
        if ln == site_name:
            continue
        if "›" in ln and len(ln) < 120:
            continue
        if ln.startswith("www.") and len(ln) < 80:
            continue
        if "." in ln and " " not in ln and len(ln) < 50:
            continue
        # Skip short single-word fragments that look like breadcrumb tails
        if len(ln) < 25 and " " not in ln and ln != site_name:
            continue
        cleaned.append(ln)

    # Pick title (first substantial line)
    title = ""
    snippet = ""
    for ln in cleaned:
        if not title and len(ln) > 3:
            title = ln
        elif title and len(ln) > 15:
            snippet = ln
            break

    if not title:
        title = site_name or href

    # If title is just the site name, try to use a longer line
    if title == site_name and len(cleaned) > 1:
        for ln in cleaned[1:]:
            if len(ln) > 10 and ln != site_name:
                title = ln
                break

    # Clean up snippet
    if len(snippet) > 350:
        snippet = snippet[:350] + "..."

    return _ParsedResult(title=title, url=href, snippet=snippet)


class _ParsedResult:
    __slots__ = ("title", "url", "snippet")

    def __init__(self, title: str, url: str, snippet: str):
        self.title = title
        self.url = url
        self.snippet = snippet


def _extract_text(el) -> str:
    """Safely extract text from a scrapling element."""
    if el.text is not None:
        return str(el.text).strip()
    return el.get_all_text().strip() if hasattr(el, "get_all_text") else ""
