"""DuckDuckGo search engine implementation with improved selectors and fault tolerance."""

from __future__ import annotations

import contextlib
import logging
import re
import time
from urllib.parse import quote_plus, urljoin, urlparse

from ..exceptions import NetworkError, ParseError
from ..utils.url import get_domain, resolve_redirect, should_skip_url
from .base import ContentType, ExtractionQuality, PageContent, SearchEngine, SearchResult, _first, _guess_content_type

logger = logging.getLogger(__name__)

# Suppress Scrapling false-positive deprecation warning
class _SuppressScraplingNoise(logging.Filter):
    def filter(self, record):
        return "This logic is deprecated" not in record.getMessage()

logging.getLogger("scrapling").addFilter(_SuppressScraplingNoise())


# Multiple selector sets for fault tolerance
_SERP_SELECTORS = {
    "duckduckgo": {
        "search_url": "https://html.duckduckgo.com/html/?q={query}&kl=us-en",
        "containers": [
            "article[data-testid='result']",
            ".result",
            ".web-result",
            ".result__body",
        ],
        "title": ["h2", ".result__title", "h3", ".result__a"],
        "url": ["a[data-testid='result-title-a']", "a.result__a", "a[href]"],
        "snippet": [".result__snippet", ".result__body", "p", ".snippet"],
    },
    "duckduckgo_lite": {
        "search_url": "https://lite.duckduckgo.com/lite/?q={query}&kl=us-en",
        "containers": [
            "table.result__snippet",
            "table tr",
            ".result-link",
            "a[rel='nofollow']",
        ],
        "title": ["a[rel='nofollow']", ".result-link", "h2", "h3"],
        "url": ["a[rel='nofollow']", "a[href]"],
        "snippet": ["td.result__snippet", "td:last-child", ".snippet", "p"],
    },
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

_STRIP_SELECTORS = [
    "script", "style", "noscript", "iframe", "svg",
    "nav", "footer", "header", "aside",
    "form", "button", "input", "select",
    '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
    ".nav", ".navbar", ".footer", ".sidebar", ".ad", ".advertisement",
    ".social-share", ".comments", ".related-posts", "#comments",
]

_CONTENT_SELECTORS = [
    "main", "article", '[role="main"]',
    "#content", "#main-content", "#article", "#post",
    ".post-content", ".article-content", ".entry-content",
    ".markdown-body", ".prose", ".documentation",
    "#readme", ".readme", "#wiki-body",
]






class DuckDuckGoEngine(SearchEngine):
    """DuckDuckGo search engine with fault-tolerant SERP scraping."""

    name = "duckduckgo"
    supports_stealth = False
    quality_tier = 1
    typical_latency_ms = 800
    reliability_score = 0.95

    def __init__(self, variant: str = "duckduckgo_lite"):
        self.variant = variant
        self._session = None
        self._stealth_session = None

    async def close(self) -> None:
        """Close any open sessions to free resources.

        Note: scrapling >= 0.2.99 uses stateless fetchers (AsyncFetcher /
        StealthyFetcher) that do not require explicit close().  We simply
        drop the reference so the GC can reclaim them.
        """
        self._session = None
        self._stealth_session = None

    async def _get_session(self, stealth: bool = False):
        """Lazy-init and reuse fetcher instances.

        scrapling >= 0.2.99 replaced AsyncDynamicSession / AsyncStealthySession
        with public AsyncFetcher / StealthyFetcher classes.
        """
        import scrapling

        if stealth:
            if self._stealth_session is None:
                self._stealth_session = scrapling.StealthyFetcher()
            return self._stealth_session
        if self._session is None:
            self._session = scrapling.AsyncFetcher()
        return self._session

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search DuckDuckGo with retry and fallback selectors."""
        cfg = _SERP_SELECTORS.get(self.variant, _SERP_SELECTORS["duckduckgo_lite"])
        search_url = cfg["search_url"].format(query=quote_plus(query))

        try:
            session = await self._get_session()
            page = await session.get(search_url, timeout=30)
        except Exception as exc:
            logger.error("SERP scrape failed [%s]: %s", self.variant, exc)
            raise NetworkError(f"Failed to fetch SERP: {exc}", retryable=True) from exc

        results: list[SearchResult] = []
        seen: set[str] = set()

        # Try multiple container selectors
        containers = []
        for sel in cfg["containers"]:
            containers = page.css(sel)
            if containers:
                logger.debug("Found %d containers with selector: %s", len(containers), sel)
                break

        if not containers:
            # Last resort: find all external links
            containers = page.css("a[href^='http']")
            logger.debug("Fallback to all links, found %d", len(containers))

        for _i, el in enumerate(containers[:max_results * 3]):
            title_el = _first(el, cfg["title"])
            url_el = _first(el, cfg["url"])
            snippet_el = _first(el, cfg["snippet"])

            title = title_el.text.strip() if title_el else ""
            href = url_el.attrib.get("href", "") if url_el else ""
            snippet = snippet_el.text.strip() if snippet_el else ""

            # Resolve redirects
            href = resolve_redirect(href, search_url)

            if not href or not title:
                continue

            domain = get_domain(href)
            if should_skip_url(href):
                continue

            normalized = href.rstrip("/")
            if normalized in seen:
                continue

            seen.add(normalized)
            results.append(SearchResult(
                title=title,
                url=href,
                snippet=snippet,
                position=len(results) + 1,
                likely_content_type=_guess_content_type(href, snippet),
                domain=domain,
                url_suggests_docs=any(d in domain for d in _DOCS_DOMAINS),
                engine=self.variant,
            ))

            if len(results) >= max_results:
                break

        if not results:
            logger.warning("No results found for query: %s", query)
            raise ParseError(
                "No results found. The page structure may have changed.",
                retryable=True,
                suggested_engine="duckduckgo" if self.variant == "duckduckgo_lite" else None,
            )

        return results

    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch a page with content extraction."""
        t0 = time.monotonic()

        try:
            session = await self._get_session(stealth)
            # scrapling >= 0.2.99 API differences:
            # - AsyncFetcher.get()  → timeout in SECONDS
            # - StealthyFetcher.async_fetch() → timeout in MILLISECONDS
            if stealth:
                page = await session.async_fetch(url, timeout=int(timeout * 1000))
            else:
                page = await session.get(url, timeout=int(timeout))
            final_url = page.url if hasattr(page, 'url') else url
        except Exception as exc:
            duration = (time.monotonic() - t0) * 1000
            err = str(exc).lower()
            # Smart error classification for fallback decisions
            if "timeout" in err or "timed out" in err:
                error_type = "timeout"
                needs_stealth_flag = not stealth
            elif "dns" in err or "name resolution" in err or "getaddrinfo" in err:
                error_type = "dns"
                needs_stealth_flag = False
            elif "connection" in err or "refused" in err or "reset" in err:
                error_type = "network"
                needs_stealth_flag = False
            elif "ssl" in err or "certificate" in err:
                error_type = "ssl"
                needs_stealth_flag = True
            elif "403" in err or "forbidden" in err or "blocked" in err:
                error_type = "blocked"
                needs_stealth_flag = True
            elif "404" in err or "not found" in err:
                error_type = "not_found"
                needs_stealth_flag = False
            else:
                error_type = "unknown"
                needs_stealth_flag = not stealth

            logger.debug("Fetch %s for %s: %s", error_type, url, exc)
            return PageContent(
                url=url,
                error_message=f"[{error_type.upper()}] {exc}",
                quality=ExtractionQuality.BLOCKED,
                fetch_duration_ms=duration,
                needs_stealth=needs_stealth_flag,
            )

        duration = (time.monotonic() - t0) * 1000

        # Save original HTML for trafilatura
        original_html = page.html_content if hasattr(page, 'html_content') else ""

        # Extract title
        title_el = _first(page, ["title", "h1"])
        title = str(title_el.text).strip() if title_el else url

        # Strip noise
        for sel in _STRIP_SELECTORS:
            for el in page.css(sel):
                with contextlib.suppress(Exception):
                    el._root.drop_tree()

        # Find main content
        main_el = None
        for sel in _CONTENT_SELECTORS:
            main_el = _first(page, [sel])
            if main_el:
                break
        if main_el is None:
            main_el = _first(page, ["body"])

        # Extract structured content
        markdown, plain, stats = _extract_structured(main_el)

        # Collect links
        internal_links, external_links = _collect_links(page, url)

        # Quality assessment
        quality = _assess_quality(stats, len(plain))

        # Enhanced extraction with trafilatura
        _date_result = ""
        _code_stats = None

        if original_html:
            try:
                import htmldate as _htmldate
                import trafilatura

                # Try trafilatura on original HTML
                tf_result = trafilatura.extract(
                    original_html,
                    output_format="markdown",
                    include_formatting=True,
                    include_links=True,
                )
                if tf_result and len(tf_result) > max(len(markdown), 200):
                    markdown = tf_result
                    plain = trafilatura.extract(
                        original_html,
                        output_format="txt",
                        include_formatting=False,
                    ) or plain
                    stats["code_blocks"] = len(re.findall(r"```", markdown)) // 2

                # Extract metadata
                meta = trafilatura.extract_metadata(original_html)
                if meta:
                    if meta.title and meta.title.strip():
                        title = meta.title.strip()
                    if meta.date:
                        _date_result = meta.date

                # htmldate fallback
                if not _date_result:
                    with contextlib.suppress(Exception):
                        _date_result = _htmldate.find_date(
                            original_html,
                            outputformat="%Y-%m-%d",
                        ) or ""

                # Code-aware analysis
                from ..extraction.code import analyze_code_content
                _code_stats = analyze_code_content(markdown, published_date=_date_result)

            except ImportError:
                logger.debug("trafilatura/htmldate not available")
            except Exception as exc:
                logger.warning("Enhanced extraction failed: %s", exc)

        return PageContent(
            url=url,
            final_url=final_url,
            title=title,
            text=plain,
            markdown=markdown,
            html=main_el.html_content if main_el else "",
            quality=quality,
            content_type=_guess_content_type(url, plain[:300]),
            content_length=len(plain),
            heading_count=stats["headings"],
            code_block_count=stats["code_blocks"],
            internal_links=internal_links,
            external_links=external_links,
            fetch_duration_ms=duration,
            published_date=_date_result,
            code_languages=_code_stats.code_languages if _code_stats else [],
            api_signatures=_code_stats.api_signatures if _code_stats else [],
            code_to_text_ratio=_code_stats.code_to_text_ratio if _code_stats else 0.0,
            freshness_days=_code_stats.freshness_days if _code_stats else None,
            is_api_reference=_code_stats.is_api_reference if _code_stats else False,
            is_tutorial=_code_stats.is_tutorial if _code_stats else False,
            is_error_solution=_code_stats.is_error_solution if _code_stats else False,
        )


def _extract_structured(element) -> tuple[str, str, dict]:
    """Extract markdown + plain text from a Scrapling element."""
    stats = {"headings": 0, "code_blocks": 0, "paragraphs": 0, "lists": 0}
    md_lines: list[str] = []
    plain_lines: list[str] = []

    if element is None:
        return "", "", stats

    # Headings
    for level in range(1, 4):
        for h in element.css(f"h{level}"):
            text = str(h.text).strip()
            if text and len(text) > 3:
                md_lines.append(f"\n{'#' * level} {text}")
                plain_lines.append(text)
                stats["headings"] += 1

    # Code blocks
    for pre in element.css("pre, code"):
        text = str(pre.text).strip()
        if text and len(text) > 10:
            lang = ""
            lang_match = re.search(r"language-(\w+)", pre.attrib.get("class", ""))
            if lang_match:
                lang = lang_match.group(1)
            md_lines.append(f"\n```{lang}\n{text}\n```")
            plain_lines.append(text)
            stats["code_blocks"] += 1

    # Paragraphs & lists
    for el in element.css("p, li, td, th, blockquote, dt, dd"):
        text = str(el.text).strip()
        if not text or len(text) < 10:
            continue
        tag = el.tag if hasattr(el, 'tag') else ""

        if tag == "blockquote":
            md_lines.append(f"> {text}")
        elif tag in ("li", "dt", "dd"):
            md_lines.append(f"- {text}")
            stats["lists"] += 1
        else:
            md_lines.append(f"\n{text}")
            stats["paragraphs"] += 1
        plain_lines.append(text)

    # Remaining body text
    remaining = str(element.text).strip()
    if remaining:
        md_lines.append(f"\n{remaining}")
        plain_lines.append(remaining)

    markdown = _clean_whitespace("\n".join(md_lines))
    plain = _clean_whitespace("\n\n".join(plain_lines))

    return markdown, plain, stats


def _assess_quality(stats: dict, content_length: int) -> ExtractionQuality:
    """Score extraction quality based on structural signals."""
    if content_length < 100:
        return ExtractionQuality.EMPTY

    score = 0
    score += min(stats["headings"], 5) * 2
    score += min(stats["paragraphs"], 10) * 1
    score += min(stats["code_blocks"], 5) * 3
    score += min(stats["lists"], 5) * 1
    score += min(content_length // 500, 10)

    if score >= 20:
        return ExtractionQuality.HIGH
    if score >= 8:
        return ExtractionQuality.MEDIUM
    return ExtractionQuality.LOW


def _collect_links(page, source_url: str, max_each: int = 10) -> tuple[list[dict], list[dict]]:
    """Collect internal/external links from the page."""
    source_domain = get_domain(source_url)
    internal: list[dict] = []
    external: list[dict] = []
    seen: set[str] = set()

    for a in page.css("a[href]"):
        href = a.attrib.get("href", "").strip()
        text = str(a.text).strip()
        if not href or not text or len(text) < 5:
            continue
        if href.startswith("#") or href.startswith("javascript:"):
            continue

        resolved = urljoin(source_url, href)
        norm = resolved.rstrip("/")
        if norm in seen:
            continue
        seen.add(norm)

        domain = get_domain(resolved)
        entry = {"text": text[:150], "url": resolved}

        if domain == source_domain:
            if len(internal) < max_each:
                internal.append(entry)
        else:
            if len(external) < max_each and not should_skip_url(resolved):
                external.append(entry)

    return internal, external


def _clean_whitespace(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


# Factory function for creating engines
async def create_engine(variant: str = "duckduckgo_lite") -> DuckDuckGoEngine:
    """Create a DuckDuckGo engine instance."""
    return DuckDuckGoEngine(variant=variant)
