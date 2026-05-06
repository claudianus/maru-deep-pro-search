"""Scrapling-native crawler with quality-aware extraction.

Returns rich metadata alongside content so the host LLM can make informed
decisions about which pages to pursue, when to retry with stealth, and
whether extracted content is sufficient."""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from urllib.parse import quote_plus, unquote, urljoin, urlparse

from scrapling import StealthyFetcher, DynamicFetcher

logger = logging.getLogger(__name__)

# Suppress Scrapling false-positive deprecation warning (fires even with no args)
class _SuppressScraplingNoise(logging.Filter):
    def filter(self, record):
        return "This logic is deprecated" not in record.getMessage()

logging.getLogger("scrapling").addFilter(_SuppressScraplingNoise())


# ═══════════════════════════════════════════════════════════════
# Rich metadata types — LLM uses these to reason about quality
# ═══════════════════════════════════════════════════════════════

class ContentType(str, Enum):
    ARTICLE = "article"
    DOCUMENTATION = "docs"
    FORUM = "forum"
    CODE = "code"
    SPAM = "spam"
    UNKNOWN = "unknown"

class ExtractionQuality(str, Enum):
    HIGH = "high"        # clean article/docs with clear structure
    MEDIUM = "medium"    # readable but noisy
    LOW = "low"          # mostly boilerplate or partial content
    EMPTY = "empty"      # nothing useful extracted
    BLOCKED = "blocked"  # anti-bot wall hit


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    position: int = 0
    # Quality hints for LLM to decide whether to fetch
    likely_content_type: ContentType = ContentType.UNKNOWN
    domain: str = ""
    url_suggests_docs: bool = False


@dataclass
class PageContent:
    url: str
    final_url: str = ""       # after redirects
    title: str = ""
    text: str = ""
    markdown: str = ""
    html: str = ""

    # Quality signals the LLM uses to decide next actions
    quality: ExtractionQuality = ExtractionQuality.EMPTY
    content_type: ContentType = ContentType.UNKNOWN
    content_length: int = 0
    heading_count: int = 0
    code_block_count: int = 0

    # Navigation hints for iterative crawling
    internal_links: list[dict] = field(default_factory=list)
    external_links: list[dict] = field(default_factory=list)
    needs_stealth: bool = False
    fetch_duration_ms: float = 0.0
    error_message: str = ""

    # Code-aware metadata for coding agent optimization
    published_date: str = ""
    code_languages: list[str] = field(default_factory=list)
    api_signatures: list[dict] = field(default_factory=list)
    code_to_text_ratio: float = 0.0
    freshness_days: int | None = None
    is_api_reference: bool = False
    is_tutorial: bool = False
    is_error_solution: bool = False


# ═══════════════════════════════════════════════════════════════
# Fetcher factory
# ═══════════════════════════════════════════════════════════════

def _stealth() -> StealthyFetcher:
    return StealthyFetcher()

def _dynamic() -> DynamicFetcher:
    return DynamicFetcher()


# ═══════════════════════════════════════════════════════════════
# SERP scraping — direct search engine HTML parsing
# ═══════════════════════════════════════════════════════════════

_SERP_SELECTORS: dict[str, dict] = {
    "duckduckgo": {
        "search_url": "https://html.duckduckgo.com/html/?q={query}",
        "container": "article[data-testid='result'], .result, .web-result",
        "title": "h2, .result__title",
        "url": "a[data-testid='result-title-a'], a.result__a",
        "snippet": ".result__snippet, .result__body",
    },
    "duckduckgo_lite": {
        "search_url": "https://lite.duckduckgo.com/lite/?q={query}",
        "container": "table+table tr, a[rel='nofollow']",
        "title": "a[rel='nofollow']",
        "url": "a[rel='nofollow']",
        "snippet": "td:last-child",
    },
    "google": {
        "search_url": "https://www.google.com/search?q={query}&hl=en&gl=us",
        "container": "div.g, div[data-sokoban-container], div.MjjYud",
        "title": "h3",
        "url": "a[jsname='UWckNb'], a[data-ved], a[href^='http']",
        "snippet": "div.VwiC3b, span.aCOpRe, div[data-sncf]",
    },
    "bing": {
        "search_url": "https://www.bing.com/search?q={query}",
        "container": "li.b_algo",
        "title": "h2",
        "url": "a[href^='http']",
        "snippet": "p.b_lineclamp2, .b_caption p",
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

_SKIP_DOMAINS = {
    "youtube.com", "youtu.be", "instagram.com", "facebook.com",
    "twitter.com", "x.com", "tiktok.com", "pinterest.com",
    "reddit.com", "linkedin.com",
}

def _first(el, selector: str):
    """Return first matching element from a CSS selector, or None."""
    results = el.css(selector)
    return results[0] if results else None


def _guess_content_type(url: str, snippet: str = "") -> ContentType:
    lower = (url + " " + snippet).lower()
    domain = urlparse(url).netloc.lower()

    for d in _DOCS_DOMAINS:
        if d in domain:
            return ContentType.DOCUMENTATION

    if any(k in lower for k in ["github.com", "gitlab.com", "bitbucket.org"]):
        return ContentType.CODE
    if any(k in lower for k in ["stackoverflow.com", "stackexchange.com", "discourse", "forum"]):
        return ContentType.FORUM
    if any(k in lower for k in ["docs.", "/docs/", "documentation", "reference", "api.", "/api/"]):
        return ContentType.DOCUMENTATION
    if any(k in lower for k in ["medium.com", "dev.to", "blog.", "/blog/"]):
        return ContentType.ARTICLE
    return ContentType.UNKNOWN


async def scrape_serp(
    query: str,
    engine: str = "duckduckgo_lite",
    max_results: int = 10,
) -> list[SearchResult]:
    """Direct SERP scrape. No API — Scrapling parses search engine HTML."""
    cfg = _SERP_SELECTORS.get(engine, _SERP_SELECTORS["duckduckgo_lite"])
    search_url = cfg["search_url"].format(query=quote_plus(query))

    fetcher = _stealth() if engine == "google" else _dynamic()

    try:
        page = await fetcher.async_fetch(search_url)
    except Exception as exc:
        logger.error("SERP scrape failed [%s]: %s", engine, exc)
        # Fallback to DuckDuckGo Lite if Google fails
        if engine == "google":
            return await scrape_serp(query, "duckduckgo_lite", max_results)
        return []

    results: list[SearchResult] = []
    seen: set[str] = set()

    containers = page.css(cfg["container"])
    if not containers:
        containers = page.css("a[href^='http']")

    for i, el in enumerate(containers[:max_results * 3]):
        title_el = _first(el, cfg.get("title", "h2, h3"))
        url_el = _first(el, cfg.get("url", "a[href]"))
        snippet_el = _first(el, cfg.get("snippet", "p"))

        title = title_el.text.strip() if title_el else ""
        href = url_el.attrib.get("href", "") if url_el else ""
        snippet = snippet_el.text.strip() if snippet_el else ""

        # Resolve Google redirect URLs
        if href.startswith("/url?") or href.startswith("/search?"):
            m = re.search(r"(?:url|q)=([^&]+)", href)
            href = m.group(1) if m else href
        # Resolve DuckDuckGo redirect URLs
        if "duckduckgo.com/l/" in href and "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            href = unquote(m.group(1)) if m else href
        if not href.startswith("http"):
            href = urljoin(search_url, href)

        if not href or not title:
            continue
        domain = urlparse(href).netloc.lower()
        if any(d in domain for d in _SKIP_DOMAINS):
            continue
        if any(d in href.lower() for d in ["/login", "/signup", "/auth", "/search", "google.com/sorry"]):
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
        ))

        if len(results) >= max_results:
            break

    return results


# ═══════════════════════════════════════════════════════════════
# Content extraction with quality assessment
# ═══════════════════════════════════════════════════════════════

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

# Signals that suggest the page is JS-rendered (empty body = script-heavy)
_JS_RENDERED_SIGNALS = [
    "react", "vue", "angular", "__NEXT", "__NUXT",
    "window.__", "document.getElementById", "createRoot",
]


async def fetch_page(
    url: str,
    stealth: bool = False,
    timeout_ms: int = 15000,
) -> PageContent:
    """Fetch a page with Scrapling. Returns rich metadata for LLM decision-making."""
    t0 = time.monotonic()

    # Phase 1: Fetch
    fetcher = _stealth() if stealth else _dynamic()
    try:
        page = await fetcher.async_fetch(url)
        final_url = page.url if hasattr(page, 'url') else url
    except Exception as exc:
        duration = (time.monotonic() - t0) * 1000
        return PageContent(
            url=url, error_message=str(exc),
            quality=ExtractionQuality.BLOCKED,
            fetch_duration_ms=duration,
            needs_stealth=not stealth,
        )

    duration = (time.monotonic() - t0) * 1000

    # Phase 2a: Save original HTML before any stripping (for trafilatura/htmldate)
    _original_html = page.html_content if hasattr(page, 'html_content') else ""

    # Phase 2b: Check for JS-rendered requirement
    body_text = (_first(page, "body").text if _first(page, "body") else "") or ""
    html_dump = body_text[:2000].lower()
    js_rendered = any(sig.lower() in html_dump for sig in _JS_RENDERED_SIGNALS)
    if js_rendered and not stealth:
        # Auto-retry with stealth (JS-rendered sites need full browser emulation)
        logger.info("JS-rendered page detected, retrying with stealth: %s", url)
        return await fetch_page(url, stealth=True, timeout_ms=timeout_ms)

    # Phase 3: Title
    title_el = _first(page, "title, h1")
    title = title_el.text.strip() if title_el else url

    # Phase 4: Strip noise
    for sel in _STRIP_SELECTORS:
        for el in page.css(sel):
            try:
                el._root.drop_tree()
            except Exception:
                pass

    # Phase 5: Find main content container
    main_el = None
    for sel in _CONTENT_SELECTORS:
        main_el = _first(page, sel)
        if main_el:
            break
    if main_el is None:
        main_el = _first(page, "body")

    # Phase 6: Extract structured content
    markdown, plain, stats = _extract_structured(main_el)

    # Phase 7: Link collection (for LLM-guided follow-up)
    internal_links, external_links = _collect_links(page, url, max_each=10)

    # Phase 8: Quality assessment
    quality = _assess_quality(stats, len(plain))

    # Phase 9: Code-aware analysis for coding-agent optimization
    _date_result = ""
    _code_stats = None
    try:
        import trafilatura
        import htmldate as _htmldate
    except ImportError as e:
        logger.warning("Phase 9 skipped (missing deps): %s", e)
    else:
        if _original_html:
            try:
                # Use trafilatura on ORIGINAL HTML (before noise stripping) for best extraction
                tf_result = trafilatura.extract(
                    _original_html,
                    output_format="markdown",
                    include_formatting=True,
                    include_links=True,
                )
                if tf_result and len(tf_result) > max(len(markdown), 200):
                    # trafilatura found better content — use it
                    markdown = tf_result
                    plain = trafilatura.extract(_original_html, output_format="txt", include_formatting=False) or plain
                    stats["code_blocks"] = len(re.findall(r"```", markdown)) // 2
                    logger.debug("trafilatura extracted %d chars (vs Scrapling %d)", len(tf_result), len(markdown))

                # Extract metadata from original HTML
                meta = trafilatura.extract_metadata(_original_html)
                if meta:
                    if meta.title and meta.title.strip():
                        title = meta.title.strip()
                    if meta.date:
                        _date_result = meta.date
                        logger.debug("trafilatura meta.date: %s", _date_result)

                # htmldate on original HTML for publication date (pass URL for better accuracy)
                if not _date_result:
                    try:
                        _date_result = _htmldate.find_date(_original_html, outputformat="%Y-%m-%d") or ""
                        if _date_result:
                            logger.debug("htmldate found date: %s", _date_result)
                    except Exception as _hde:
                        logger.debug("htmldate failed: %s", _hde)

                # Code-aware analysis on final markdown
                from .code_aware import analyze_code_content
                _code_stats = analyze_code_content(markdown, published_date=_date_result)
                if _code_stats:
                    logger.debug(
                        "code_aware: langs=%s primary=%s api_sigs=%d ratio=%.2f freshness=%s days",
                        _code_stats.code_languages, _code_stats.primary_language,
                        len(_code_stats.api_signatures), _code_stats.code_to_text_ratio,
                        _code_stats.freshness_days,
                    )
            except Exception as _p9e:
                logger.warning("Phase 9 extraction failed for %s: %s", url, _p9e)

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
        # Code-aware metadata for coding agent optimization
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
    """Extract markdown + plain text from a Scrapling element. Returns stats dict."""
    stats = {"headings": 0, "code_blocks": 0, "paragraphs": 0, "lists": 0}
    md_lines: list[str] = []
    plain_lines: list[str] = []

    if element is None:
        return "", "", stats

    # Headings (preserve hierarchy)
    for level in range(1, 4):  # h1-h3 only, h4+ is usually noise
        for h in element.css(f"h{level}"):
            text = h.text.strip()
            if text and len(text) > 3:
                md_lines.append(f"\n{'#' * level} {text}")
                plain_lines.append(text)
                stats["headings"] += 1

    # Code blocks
    for pre in element.css("pre, code"):
        text = pre.text.strip()
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
        text = el.text.strip()
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
    remaining = element.text.strip()
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
    source_domain = urlparse(source_url).netloc
    internal: list[dict] = []
    external: list[dict] = []
    seen: set[str] = set()

    for a in page.css("a[href]"):
        href = a.attrib.get("href", "").strip()
        text = a.text.strip()
        if not href or not text or len(text) < 5:
            continue
        if href.startswith("#") or href.startswith("javascript:"):
            continue

        resolved = urljoin(source_url, href)
        norm = resolved.rstrip("/")
        if norm in seen:
            continue
        seen.add(norm)

        domain = urlparse(resolved).netloc
        entry = {"text": text[:150], "url": resolved}

        if domain == source_domain:
            if len(internal) < max_each:
                internal.append(entry)
        else:
            if len(external) < max_each and not any(d in resolved.lower() for d in _SKIP_DOMAINS):
                external.append(entry)

    return internal, external


def _clean_whitespace(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


# ═══════════════════════════════════════════════════════════════
# Concurrency
# ═══════════════════════════════════════════════════════════════

async def fetch_many(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = 5,
) -> list[PageContent]:
    sem = asyncio.Semaphore(max_concurrent)

    async def _one(u: str) -> PageContent:
        async with sem:
            return await fetch_page(u, stealth=stealth)

    return await asyncio.gather(*(_one(u) for u in urls))


# Public API — flat namespace for tool imports
__all__ = [
    "SearchResult", "PageContent",
    "ContentType", "ExtractionQuality",
    "scrape_serp", "fetch_page", "fetch_many",
]
