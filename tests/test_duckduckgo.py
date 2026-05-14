"""Unit tests for DuckDuckGo engine.

Mocks scrapling sessions and HTML elements to test search / fetch
branches without network calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from maru_deep_pro_search.engines.base import ExtractionQuality
from maru_deep_pro_search.engines.duckduckgo import (
    DuckDuckGoEngine,
    _assess_quality,
    _clean_whitespace,
    _collect_links,
    _extract_github_meta,
    _extract_structured,
    create_engine,
)
from maru_deep_pro_search.exceptions import NetworkError, ParseError

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _make_element(
    tag: str = "div",
    text: str = "",
    attrib: dict | None = None,
    children: list | None = None,
) -> MagicMock:
    """Build a mock scrapling element."""
    el = MagicMock()
    el.tag = tag
    el.text = text
    el.attrib = attrib or {}
    el.html_content = f"<{tag}>{text}</{tag}>"
    el._root = MagicMock()
    _children = children or []

    def _css(selector: str) -> list:
        # Exact tag matching
        sel_tags = [s.strip() for s in selector.split(",")]
        if selector.startswith("h") and selector[1:].isdigit():
            return [c for c in _children if getattr(c, "tag", "") == selector]
        if selector == "pre, code" or "pre" in sel_tags or "code" in sel_tags:
            return [c for c in _children if getattr(c, "tag", "") in ("pre", "code")]
        if (
            "p" in sel_tags
            or "li" in sel_tags
            or "td" in sel_tags
            or "th" in sel_tags
            or "blockquote" in sel_tags
            or "dt" in sel_tags
            or "dd" in sel_tags
        ):
            return [
                c
                for c in _children
                if getattr(c, "tag", "") in ("p", "li", "td", "th", "blockquote", "dt", "dd")
            ]
        if selector == "title" or selector == "h1":
            return [c for c in _children if getattr(c, "tag", "") == selector]
        if selector in (
            "main",
            "article",
            '[role="main"]',
            "#content",
            "#main-content",
            "#article",
            "#post",
            ".post-content",
            ".article-content",
            ".entry-content",
            ".markdown-body",
            ".prose",
            ".documentation",
            "#readme",
            ".readme",
            "#wiki-body",
        ):
            return [c for c in _children if getattr(c, "tag", "") == "main"]
        if selector == "body":
            return [c for c in _children if getattr(c, "tag", "") == "body"]
        if selector == "a[href]":
            return [c for c in _children if "href" in getattr(c, "attrib", {})]
        # For GitHub-specific selectors
        for gh_sel in [
            "a[href$='/stargazers']",
            ".js-social-count",
            "[href*='stargazers']",
            ".repository-content .BorderGrid-cell",
            "[title*='License']",
            "a[href*='LICENSE']",
            ".repository-content .Progress-item",
            ".text-bold[title]",
            "[data-testid='language']",
            "relative-time",
            "time-ago",
            "[datetime]",
            "[data-testid='topic-name']",
            ".topic-tag",
            "[data-testid='about-description']",
            ".repository-content p",
        ]:
            if selector == gh_sel:
                return [
                    c
                    for c in _children
                    if selector.replace("[", "")
                    .replace("]", "")
                    .replace("'", "")
                    .replace('"', "")
                    .replace("$=", "")
                    .replace("*=", "")
                    .replace(".", "")
                    .replace("#", "")
                    .replace(" ", "")
                    in str(getattr(c, "attrib", {}))
                    or any(
                        kw in str(getattr(c, "attrib", {}))
                        for kw in [
                            "stargazers",
                            "License",
                            "LICENSE",
                            "language",
                            "datetime",
                            "topic-name",
                            "about-description",
                            "Progress-item",
                            "BorderGrid-cell",
                        ]
                    )
                ]
        return []

    el.css = _css
    return el


def _make_page(elements: list | None = None, html: str = "") -> MagicMock:
    """Build a mock scrapling page."""
    page = MagicMock()
    page.html_content = html
    page.url = "https://example.com"
    _els = elements or []

    def _css(selector: str) -> list:
        if selector == "a[href^='http']":
            return [e for e in _els if "href" in getattr(e, "attrib", {})]
        if selector == "body":
            return [e for e in _els if getattr(e, "tag", "") == "body"]
        return _els

    page.css = _css
    return page


def _async_session(page: MagicMock) -> MagicMock:
    """Return a session mock whose get() is awaitable."""
    session = MagicMock()
    session.get = AsyncMock(return_value=page)
    return session


# ═══════════════════════════════════════════════════════════════
# Engine lifecycle
# ═══════════════════════════════════════════════════════════════


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_close(self) -> None:
        engine = DuckDuckGoEngine()
        engine._session = MagicMock()
        engine._stealth_session = MagicMock()
        await engine.close()
        assert engine._session is None
        assert engine._stealth_session is None

    @pytest.mark.asyncio
    async def test_get_session_normal(self, monkeypatch: Any) -> None:
        fetcher = MagicMock()
        monkeypatch.setattr("scrapling.AsyncFetcher", lambda: fetcher)
        engine = DuckDuckGoEngine()
        sess = await engine._get_session()
        assert sess is fetcher

    @pytest.mark.asyncio
    async def test_get_session_stealth(self, monkeypatch: Any) -> None:
        fetcher = MagicMock()
        monkeypatch.setattr("scrapling.StealthyFetcher", lambda: fetcher)
        engine = DuckDuckGoEngine()
        sess = await engine._get_session(stealth=True)
        assert sess is fetcher

    @pytest.mark.asyncio
    async def test_create_engine(self) -> None:
        engine = await create_engine("duckduckgo")
        assert engine.variant == "duckduckgo"


# ═══════════════════════════════════════════════════════════════
# Search
# ═══════════════════════════════════════════════════════════════


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_network_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()

        async def _raise(*_args, **_kwargs):
            raise ConnectionError("boom")

        monkeypatch.setattr(engine, "_get_session", _raise)
        with pytest.raises(NetworkError):
            await engine.search("test")

    @pytest.mark.asyncio
    async def test_search_no_results(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        page = _make_page(elements=[])
        session = _async_session(page)

        async def _mock_sess(*args, **k):
            return session

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        with pytest.raises(ParseError) as exc_info:
            await engine.search("test")
        assert exc_info.value.suggested_engine == "duckduckgo"

    @pytest.mark.asyncio
    async def test_search_no_results_duckduckgo_variant(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine(variant="duckduckgo")
        page = _make_page(elements=[])
        session = _async_session(page)

        async def _mock_sess(*args, **k):
            return session

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        with pytest.raises(ParseError) as exc_info:
            await engine.search("test")
        assert exc_info.value.suggested_engine is None

    @pytest.mark.asyncio
    async def test_search_should_skip_url(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        link = _make_element("a", text="Title", attrib={"href": "https://example.com/page"})
        page = _make_page(elements=[link])
        session = _async_session(page)

        async def _mock_sess(*args, **k):
            return session

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        monkeypatch.setattr("maru_deep_pro_search.engines.duckduckgo._first", lambda el, sels: el)
        monkeypatch.setattr(
            "maru_deep_pro_search.engines.duckduckgo.should_skip_url",
            lambda url: True,
        )
        with pytest.raises(ParseError):
            await engine.search("test")

    @pytest.mark.asyncio
    async def test_search_skips_duplicates(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        el1 = _make_element("a", text="T1", attrib={"href": "https://example.com/page"})
        el2 = _make_element("a", text="T2", attrib={"href": "https://example.com/page"})
        page = _make_page(elements=[el1, el2])
        session = _async_session(page)

        async def _mock_sess(*args, **k):
            return session

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        monkeypatch.setattr("maru_deep_pro_search.engines.duckduckgo._first", lambda el, sels: el)
        results = await engine.search("test", max_results=5)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_success(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        el = _make_element(
            "a",
            text="Python Docs",
            attrib={"href": "https://docs.python.org/3"},
        )
        page = _make_page(elements=[el])
        session = _async_session(page)

        async def _mock_sess(*args, **k):
            return session

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        monkeypatch.setattr("maru_deep_pro_search.engines.duckduckgo._first", lambda el, sels: el)
        results = await engine.search("python docs", max_results=5)
        assert len(results) == 1
        assert results[0].title == "Python Docs"
        assert results[0].domain == "docs.python.org"
        assert results[0].url_suggests_docs

    @pytest.mark.asyncio
    async def test_search_fallback_to_links(self, monkeypatch: Any) -> None:
        """When no container selector matches, fallback to all http links."""
        engine = DuckDuckGoEngine()
        link = _make_element(
            "a",
            text="Fallback Link",
            attrib={"href": "https://example.com/fallback"},
        )
        page = _make_page(elements=[link])

        def _css(selector: str) -> list:
            if "result" in selector or "table" in selector:
                return []
            return [link]

        page.css = _css
        session = _async_session(page)

        async def _mock_sess(*args, **k):
            return session

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        monkeypatch.setattr("maru_deep_pro_search.engines.duckduckgo._first", lambda el, sels: el)
        results = await engine.search("test", max_results=5)
        assert len(results) == 1


# ═══════════════════════════════════════════════════════════════
# Fetch error branches
# ═══════════════════════════════════════════════════════════════


class TestFetchErrors:
    @pytest.mark.asyncio
    async def test_fetch_timeout_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        sess = MagicMock()
        sess.get = AsyncMock(side_effect=TimeoutError("timed out"))

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        page = await engine.fetch("https://example.com")
        assert page.quality == ExtractionQuality.BLOCKED
        assert "TIMEOUT" in page.error_message
        assert page.needs_stealth

    @pytest.mark.asyncio
    async def test_fetch_dns_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        sess = MagicMock()
        sess.get = AsyncMock(side_effect=Exception("dns name resolution failed"))

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        page = await engine.fetch("https://example.com")
        assert "DNS" in page.error_message
        assert not page.needs_stealth

    @pytest.mark.asyncio
    async def test_fetch_connection_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        sess = MagicMock()
        sess.get = AsyncMock(side_effect=Exception("connection refused"))

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        page = await engine.fetch("https://example.com")
        assert "network" in page.error_message.lower() or "connection" in page.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_ssl_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        sess = MagicMock()
        sess.get = AsyncMock(side_effect=Exception("ssl certificate error"))

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        page = await engine.fetch("https://example.com")
        assert "SSL" in page.error_message
        assert page.needs_stealth

    @pytest.mark.asyncio
    async def test_fetch_403_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        sess = MagicMock()
        sess.get = AsyncMock(side_effect=Exception("403 forbidden"))

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        page = await engine.fetch("https://example.com")
        assert "blocked" in page.error_message.lower()
        assert page.needs_stealth

    @pytest.mark.asyncio
    async def test_fetch_404_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        sess = MagicMock()
        sess.get = AsyncMock(side_effect=Exception("404 not found"))

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        page = await engine.fetch("https://example.com")
        assert "not_found" in page.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_unknown_error(self, monkeypatch: Any) -> None:
        engine = DuckDuckGoEngine()
        sess = MagicMock()
        sess.get = AsyncMock(side_effect=Exception("random failure"))

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        page = await engine.fetch("https://example.com")
        assert "unknown" in page.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_stealth_path(self, monkeypatch: Any) -> None:
        """fetch with stealth=True uses StealthyFetcher API."""
        engine = DuckDuckGoEngine()

        async def _afetch(*a, **k):
            return _make_page()

        sess = MagicMock()
        sess.async_fetch = _afetch

        async def _mock_sess(*args, **k):
            return sess

        monkeypatch.setattr(engine, "_get_session", _mock_sess)
        # Just verify it completes without error (extraction mocked separately)
        page = await engine.fetch("https://example.com", stealth=True)
        assert page.quality == ExtractionQuality.BLOCKED or page.quality == ExtractionQuality.EMPTY


# ═══════════════════════════════════════════════════════════════
# _extract_structured
# ═══════════════════════════════════════════════════════════════


class TestExtractStructured:
    def test_none_element(self) -> None:
        md, plain, stats = _extract_structured(None)
        assert md == ""
        assert plain == ""
        assert stats == {"headings": 0, "code_blocks": 0, "paragraphs": 0, "lists": 0}

    def test_headings(self) -> None:
        h1 = _make_element("h1", text="Heading 1")
        h2 = _make_element("h2", text="Heading 2")
        el = _make_element(children=[h1, h2])
        md, plain, stats = _extract_structured(el)
        assert "# Heading 1" in md
        assert "## Heading 2" in md
        assert stats["headings"] == 2

    def test_code_block_with_language(self) -> None:
        pre = _make_element(
            "pre",
            text="print('hello')",
            attrib={"class": "language-python"},
        )
        el = _make_element(children=[pre])
        md, plain, stats = _extract_structured(el)
        assert "```python" in md
        assert stats["code_blocks"] == 1

    def test_code_block_no_class(self) -> None:
        pre = _make_element("pre", text="print('hello')")
        el = _make_element(children=[pre])
        md, plain, stats = _extract_structured(el)
        assert "```\nprint" in md

    def test_blockquote(self) -> None:
        bq = _make_element("blockquote", text="A quote that is longer than ten chars")
        el = _make_element(children=[bq])
        md, plain, stats = _extract_structured(el)
        assert "> A quote" in md

    def test_list_item(self) -> None:
        li = _make_element("li", text="Item one that is longer than ten characters")
        el = _make_element(children=[li])
        md, plain, stats = _extract_structured(el)
        assert "- Item one" in md
        assert stats["lists"] == 1

    def test_remaining_text(self) -> None:
        el = _make_element("div", text="Some remaining text")
        md, plain, stats = _extract_structured(el)
        assert "Some remaining text" in md

    def test_short_text_skipped(self) -> None:
        """Paragraphs/lists with < 10 chars are skipped."""
        p = _make_element("p", text="Hi")
        el = _make_element(children=[p])
        md, plain, stats = _extract_structured(el)
        assert md == ""
        assert stats["paragraphs"] == 0


# ═══════════════════════════════════════════════════════════════
# _assess_quality
# ═══════════════════════════════════════════════════════════════


class TestAssessQuality:
    def test_empty(self) -> None:
        assert _assess_quality({}, 50) == ExtractionQuality.EMPTY

    def test_high(self) -> None:
        stats = {"headings": 5, "paragraphs": 10, "code_blocks": 5, "lists": 5}
        assert _assess_quality(stats, 5000) == ExtractionQuality.HIGH

    def test_medium(self) -> None:
        stats = {"headings": 2, "paragraphs": 3, "code_blocks": 1, "lists": 1}
        assert _assess_quality(stats, 1000) == ExtractionQuality.MEDIUM

    def test_low(self) -> None:
        stats = {"headings": 0, "paragraphs": 1, "code_blocks": 0, "lists": 0}
        assert _assess_quality(stats, 200) == ExtractionQuality.LOW


# ═══════════════════════════════════════════════════════════════
# _collect_links
# ═══════════════════════════════════════════════════════════════


class TestCollectLinks:
    def test_skips_empty_and_short(self) -> None:
        a1 = _make_element("a", text="", attrib={"href": "https://a.com"})
        a2 = _make_element("a", text="Hi", attrib={"href": "https://b.com"})
        page = _make_page(elements=[a1, a2])
        internal, external = _collect_links(page, "https://source.com")
        assert len(external) == 0  # "Hi" is too short

    def test_skips_hash_and_javascript(self) -> None:
        a1 = _make_element("a", text="Anchor", attrib={"href": "#section"})
        a2 = _make_element("a", text="JS Link", attrib={"href": "javascript:void(0)"})
        page = _make_page(elements=[a1, a2])
        internal, external = _collect_links(page, "https://source.com")
        assert len(internal) == 0
        assert len(external) == 0

    def test_skips_duplicates(self) -> None:
        a1 = _make_element("a", text="Same page", attrib={"href": "/page"})
        a2 = _make_element("a", text="Same page", attrib={"href": "/page"})
        page = _make_page(elements=[a1, a2])
        internal, external = _collect_links(page, "https://source.com")
        assert len(internal) == 1

    def test_internal_vs_external(self) -> None:
        a1 = _make_element("a", text="Internal page", attrib={"href": "/about"})
        a2 = _make_element("a", text="External site", attrib={"href": "https://other.com"})
        page = _make_page(elements=[a1, a2])
        internal, external = _collect_links(page, "https://source.com")
        assert len(internal) == 1
        assert internal[0]["url"] == "https://source.com/about"
        assert len(external) == 1
        assert external[0]["url"] == "https://other.com"


# ═══════════════════════════════════════════════════════════════
# _clean_whitespace
# ═══════════════════════════════════════════════════════════════


class TestCleanWhitespace:
    def test_collapses_newlines(self) -> None:
        assert _clean_whitespace("a\n\n\n\nb") == "a\n\nb"

    def test_collapses_spaces(self) -> None:
        assert _clean_whitespace("a    b") == "a b"

    def test_strips(self) -> None:
        assert _clean_whitespace("  hello  ") == "hello"


# ═══════════════════════════════════════════════════════════════
# _extract_github_meta
# ═══════════════════════════════════════════════════════════════


class TestExtractGithubMeta:
    def test_stars(self) -> None:
        stars = _make_element("a", text="5.2k", attrib={"href": "/stargazers"})
        page = _make_page(elements=[stars])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta is not None
        assert meta["stars"] == "5.2k"

    def test_stars_aria_label(self) -> None:
        stars = _make_element(
            "a", text="", attrib={"href": "/stargazers", "aria-label": "1,234 stars"}
        )
        page = _make_page(elements=[stars])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta["stars"] == "1,234 stars"

    def test_license(self) -> None:
        lic = _make_element("span", text="MIT License")
        page = _make_page(elements=[lic])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta["license"] == "MIT License"

    def test_primary_language(self) -> None:
        lang = _make_element("span", text="Python", attrib={"class": "Progress-item"})
        page = _make_page(elements=[lang])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta["primary_language"] == "Python"

    def test_primary_language_title_attr(self) -> None:
        lang = _make_element("span", text="", attrib={"title": "Rust"})
        page = _make_page(elements=[lang])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta["primary_language"] == "Rust"

    def test_last_updated(self) -> None:
        time = _make_element("relative-time", text="", attrib={"datetime": "2024-01-15T00:00:00Z"})
        page = _make_page(elements=[time])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta["last_updated"] == "2024-01-15T00:00:00Z"

    def test_topics(self) -> None:
        t1 = _make_element("span", text="python", attrib={"data-testid": "topic-name"})
        t2 = _make_element("span", text="ml", attrib={"data-testid": "topic-name"})
        page = _make_page(elements=[t1, t2])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta["topics"] == ["python", "ml"]

    def test_description(self) -> None:
        desc = _make_element("p", text="This is a great repository for testing.")
        page = _make_page(elements=[desc])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert "description" in meta

    def test_no_repo_url_only(self) -> None:
        page = _make_page(elements=[])
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta is None

    def test_exception_handling(self) -> None:
        page = MagicMock()
        page.css = lambda s: (_ for _ in ()).throw(RuntimeError("boom"))
        meta = _extract_github_meta(page, "https://github.com/u/r", "")
        assert meta is None


class TestSuppressScraplingNoise:
    def test_filters_deprecation(self) -> None:
        from maru_deep_pro_search.engines.duckduckgo import _SuppressScraplingNoise

        f = _SuppressScraplingNoise()
        record = MagicMock()
        record.getMessage.return_value = "This logic is deprecated"
        assert not f.filter(record)

    def test_allows_other_messages(self) -> None:
        from maru_deep_pro_search.engines.duckduckgo import _SuppressScraplingNoise

        f = _SuppressScraplingNoise()
        record = MagicMock()
        record.getMessage.return_value = "Some other message"
        assert f.filter(record)
