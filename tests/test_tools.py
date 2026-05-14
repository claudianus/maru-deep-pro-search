"""Unit tests for MCP tool functions.

Mocks all external dependencies (search engines, caches, deep_research)
to exercise every branch without network calls.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maru_deep_pro_search.engines.base import (
    ContentType,
    ExtractionQuality,
    PageContent,
    SearchResult,
    SourceType,
)
from maru_deep_pro_search.exceptions import MaruSearchError
from maru_deep_pro_search.tools import (
    tool_answer,
    tool_deep_research,
    tool_fetch_bulk,
    tool_fetch_page,
    tool_parallel_search,
    tool_search_with_citations,
    tool_stealthy_fetch,
    tool_web_search,
)

# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def mock_engine(monkeypatch: Any) -> MagicMock:
    """Return a mock search engine whose methods can be configured per-test."""
    engine = MagicMock()
    engine.search = AsyncMock(return_value=[])
    engine.fetch = AsyncMock(
        return_value=PageContent(
            url="https://example.com",
            title="Example",
            text="Hello world",
            markdown="# Hello world",
            quality=ExtractionQuality.HIGH,
            content_type=ContentType.ARTICLE,
            content_length=100,
            fetch_duration_ms=123.0,
        )
    )
    monkeypatch.setattr(
        "maru_deep_pro_search.tools.SearchEngineRegistry.create",
        lambda _name: engine,
    )
    return engine


@pytest.fixture
def no_cache(monkeypatch: Any) -> None:
    """Ensure caches always miss."""
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    monkeypatch.setattr("maru_deep_pro_search.tools.get_search_cache", lambda: mock_cache)
    monkeypatch.setattr("maru_deep_pro_search.tools.get_fetch_cache", lambda: mock_cache)


@pytest.fixture
def hit_cache(monkeypatch: Any) -> MagicMock:
    """Ensure caches always hit with a fixed value."""
    mock_cache = MagicMock()
    mock_cache.get.return_value = "CACHED_RESULT"
    monkeypatch.setattr("maru_deep_pro_search.tools.get_search_cache", lambda: mock_cache)
    monkeypatch.setattr("maru_deep_pro_search.tools.get_fetch_cache", lambda: mock_cache)
    return mock_cache


# ═══════════════════════════════════════════════════════════════
# tool_web_search
# ═══════════════════════════════════════════════════════════════


class TestToolWebSearch:
    @pytest.mark.asyncio
    async def test_invalid_engine_fallback(
        self, mock_engine: MagicMock, no_cache: None, capsys: Any
    ) -> None:
        mock_engine.search.return_value = [
            SearchResult(title="T", url="https://example.com", snippet="S")
        ]
        result = await tool_web_search("test", engine="invalid_engine")
        assert "Search:" in result
        assert "duckduckgo_lite" in result

    @pytest.mark.asyncio
    async def test_cache_hit(self, hit_cache: MagicMock) -> None:
        result = await tool_web_search("test")
        assert result == "CACHED_RESULT"

    @pytest.mark.asyncio
    async def test_timeout(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.side_effect = asyncio.TimeoutError()
        result = await tool_web_search("test")
        assert "[TIMEOUT]" in result

    @pytest.mark.asyncio
    async def test_maru_search_error_with_fallback(
        self, mock_engine: MagicMock, no_cache: None
    ) -> None:
        fallback_engine = MagicMock()
        fallback_engine.search = AsyncMock(
            return_value=[SearchResult(title="FB", url="https://fb.com", snippet="s")]
        )

        async def _side_effect(*_args, **_kwargs):
            raise MaruSearchError("fail", suggested_engine="bing")

        mock_engine.search.side_effect = _side_effect

        call_count = [0]

        def _create(name):
            if name == "bing":
                call_count[0] += 1
                return fallback_engine
            return mock_engine

        with patch("maru_deep_pro_search.tools.SearchEngineRegistry.create", _create):
            result = await tool_web_search("test")
        assert "FB" in result
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_maru_search_error_no_suggested_engine(
        self, mock_engine: MagicMock, no_cache: None
    ) -> None:
        async def _side_effect(*_args, **_kwargs):
            raise MaruSearchError("fail")

        mock_engine.search.side_effect = _side_effect
        with pytest.raises(MaruSearchError):
            await tool_web_search("test")

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.return_value = []
        result = await tool_web_search("test")
        assert "No results found" in result

    @pytest.mark.asyncio
    async def test_result_formatting(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.return_value = [
            SearchResult(
                title="Python Docs",
                url="https://docs.python.org/3",
                snippet="Official docs",
                position=1,
                likely_content_type=ContentType.DOCUMENTATION,
                source_type=SourceType.OFFICIAL_DOCS,
                is_primary=True,
                domain="docs.python.org",
            )
        ]
        result = await tool_web_search("python")
        assert "[AUTHORITY]" in result
        assert "[PRIMARY]" in result
        assert "[OFFICIAL-DOCS]" in result


# ═══════════════════════════════════════════════════════════════
# tool_fetch_page
# ═══════════════════════════════════════════════════════════════


class TestToolFetchPage:
    @pytest.mark.asyncio
    async def test_cache_hit(self, hit_cache: MagicMock) -> None:
        result = await tool_fetch_page("https://example.com")
        assert result == "CACHED_RESULT"

    @pytest.mark.asyncio
    async def test_timeout_with_stealth_fallback(
        self, mock_engine: MagicMock, no_cache: None, monkeypatch: Any
    ) -> None:
        mock_engine.fetch.side_effect = asyncio.TimeoutError()
        stealth_called = [False]

        async def _stealth_fetch(url, max_tokens):
            stealth_called[0] = True
            return "STEALTH_RESULT"

        monkeypatch.setattr("maru_deep_pro_search.tools.tool_stealthy_fetch", _stealth_fetch)
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=True)
        assert stealth_called[0]
        assert result == "STEALTH_RESULT"

    @pytest.mark.asyncio
    async def test_timeout_no_fallback(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.side_effect = asyncio.TimeoutError()
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[TIMEOUT]" in result

    @pytest.mark.asyncio
    async def test_blocked_timeout_error(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="Connection timeout",
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[BLOCKED]" in result
        assert "timed out" in result

    @pytest.mark.asyncio
    async def test_blocked_ssl_error(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="SSL certificate verify failed",
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[BLOCKED]" in result
        assert "SSL/TLS" in result

    @pytest.mark.asyncio
    async def test_blocked_dns_error(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="DNS name resolution failed",
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[BLOCKED]" in result
        assert "DNS" in result

    @pytest.mark.asyncio
    async def test_blocked_connection_refused(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="Connection refused",
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[BLOCKED]" in result
        assert "Connection refused" in result

    @pytest.mark.asyncio
    async def test_blocked_import_error(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="cannot import module xyz",
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[BLOCKED]" in result
        assert "Internal fetcher error" in result

    @pytest.mark.asyncio
    async def test_blocked_403_error(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="HTTP 403 Forbidden",
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[BLOCKED]" in result
        assert "Access denied" in result

    @pytest.mark.asyncio
    async def test_blocked_generic_error_with_fallback(
        self, mock_engine: MagicMock, no_cache: None, monkeypatch: Any
    ) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="Some random error",
        )
        stealth_called = [False]

        async def _stealth_fetch(url, max_tokens):
            stealth_called[0] = True
            return "STEALTH"

        monkeypatch.setattr("maru_deep_pro_search.tools.tool_stealthy_fetch", _stealth_fetch)
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=True)
        assert stealth_called[0]
        assert result == "STEALTH"

    @pytest.mark.asyncio
    async def test_blocked_generic_error_no_fallback(
        self, mock_engine: MagicMock, no_cache: None
    ) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.BLOCKED,
            error_message="Some random error",
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[BLOCKED]" in result
        assert "Fetch blocked or failed" in result

    @pytest.mark.asyncio
    async def test_empty_with_fallback(
        self, mock_engine: MagicMock, no_cache: None, monkeypatch: Any
    ) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.EMPTY,
            content_length=0,
        )
        stealth_called = [False]

        async def _stealth_fetch(url, max_tokens):
            stealth_called[0] = True
            return "STEALTH"

        monkeypatch.setattr("maru_deep_pro_search.tools.tool_stealthy_fetch", _stealth_fetch)
        await tool_fetch_page("https://example.com", auto_stealth_fallback=True)
        assert stealth_called[0]

    @pytest.mark.asyncio
    async def test_empty_no_fallback(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            quality=ExtractionQuality.EMPTY,
            content_length=0,
        )
        result = await tool_fetch_page("https://example.com", auto_stealth_fallback=False)
        assert "[EMPTY]" in result

    @pytest.mark.asyncio
    async def test_code_metadata(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            title="API Docs",
            text="docs",
            markdown="# docs",
            quality=ExtractionQuality.HIGH,
            content_type=ContentType.DOCUMENTATION,
            content_length=500,
            fetch_duration_ms=50.0,
            code_languages=["python", "javascript"],
            api_signatures=[
                {"signature": "def foo(): pass"},
                {"signature": "class Bar:"},
            ],
            package_refs=[
                {"package": "requests", "language": "python"},
            ],
            code_to_text_ratio=0.25,
            published_date="2024-01-15",
            freshness_days=30,
            is_api_reference=True,
            is_tutorial=False,
            is_error_solution=False,
            external_links=[
                {"text": "Related", "url": "https://related.com"},
            ],
        )
        result = await tool_fetch_page("https://example.com")
        assert "API reference" in result
        assert "python" in result
        assert "javascript" in result
        assert "def foo(): pass" in result
        assert "requests (python)" in result
        assert "code-to-text ratio: 25%" in result
        assert "2024-01-15" in result
        assert "30d ago" in result
        assert "Follow-up links" in result

    @pytest.mark.asyncio
    async def test_tutorial_flag(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            title="Tutorial",
            text="tutorial",
            markdown="# tutorial",
            quality=ExtractionQuality.HIGH,
            content_type=ContentType.ARTICLE,
            content_length=200,
            fetch_duration_ms=50.0,
            is_api_reference=False,
            is_tutorial=True,
            is_error_solution=False,
        )
        result = await tool_fetch_page("https://example.com")
        assert "tutorial" in result

    @pytest.mark.asyncio
    async def test_error_solution_flag(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.fetch.return_value = PageContent(
            url="https://example.com",
            title="Error Fix",
            text="fix",
            markdown="# fix",
            quality=ExtractionQuality.HIGH,
            content_type=ContentType.ARTICLE,
            content_length=200,
            fetch_duration_ms=50.0,
            is_api_reference=False,
            is_tutorial=False,
            is_error_solution=True,
        )
        result = await tool_fetch_page("https://example.com")
        assert "error/solution" in result


# ═══════════════════════════════════════════════════════════════
# tool_fetch_bulk
# ═══════════════════════════════════════════════════════════════


class TestToolFetchBulk:
    @pytest.mark.asyncio
    async def test_fetch_one_timeout(self, mock_engine: MagicMock, no_cache: None) -> None:
        async def _side_effect(url, stealth):
            if "slow" in url:
                raise asyncio.TimeoutError()
            return PageContent(
                url=url,
                title="Fast",
                text="content",
                quality=ExtractionQuality.HIGH,
                content_type=ContentType.ARTICLE,
                content_length=100,
            )

        mock_engine.fetch.side_effect = _side_effect
        result = await tool_fetch_bulk(["https://slow.com", "https://fast.com"])
        assert "[BLOCKED]" in result
        assert "Fetch timeout" in result
        assert "Fast" in result

    @pytest.mark.asyncio
    async def test_exception_in_pages(self, mock_engine: MagicMock, no_cache: None) -> None:
        async def _side_effect(url, stealth):
            if "bad" in url:
                raise RuntimeError("boom")
            return PageContent(
                url=url,
                title="OK",
                text="content",
                quality=ExtractionQuality.HIGH,
                content_type=ContentType.ARTICLE,
                content_length=100,
            )

        mock_engine.fetch.side_effect = _side_effect
        result = await tool_fetch_bulk(["https://bad.com", "https://ok.com"])
        assert "boom" in result
        assert "OK" in result

    @pytest.mark.asyncio
    async def test_badges_and_empty(self, mock_engine: MagicMock, no_cache: None) -> None:
        async def _side_effect(url, stealth):
            if "blocked" in url:
                return PageContent(
                    url=url,
                    title="Blocked",
                    error_message="Access denied",
                    quality=ExtractionQuality.BLOCKED,
                    content_type=ContentType.UNKNOWN,
                    content_length=0,
                )
            if "empty" in url:
                return PageContent(
                    url=url,
                    title="Empty",
                    text="",
                    quality=ExtractionQuality.EMPTY,
                    content_type=ContentType.UNKNOWN,
                    content_length=0,
                )
            return PageContent(
                url=url,
                title="High",
                text="content",
                quality=ExtractionQuality.HIGH,
                content_type=ContentType.ARTICLE,
                content_length=50,
            )

        mock_engine.fetch.side_effect = _side_effect
        result = await tool_fetch_bulk(
            ["https://blocked.com", "https://empty.com", "https://high.com"]
        )
        assert "[BLOCKED]" in result
        assert "[empty]" in result
        assert "[HIGH]" in result
        assert "blocked" in result.lower() or "Access denied" in result

    @pytest.mark.asyncio
    async def test_no_content_fetched(self, mock_engine: MagicMock, no_cache: None) -> None:
        # Empty urls list → no pages → lines stays empty
        result = await tool_fetch_bulk([])
        assert "No content fetched" in result


# ═══════════════════════════════════════════════════════════════
# tool_deep_research
# ═══════════════════════════════════════════════════════════════


class TestToolDeepResearch:
    @pytest.mark.asyncio
    async def test_invalid_engine_fallback(self, no_cache: None, monkeypatch: Any) -> None:
        called = [False]

        async def _deep_research(**kwargs):
            called[0] = True
            assert kwargs["engine"] == "duckduckgo_lite"
            from maru_deep_pro_search.research.deep import ResearchResult

            return ResearchResult(
                query="test", engine="duckduckgo_lite", total_sources=0, sources=[]
            )

        monkeypatch.setattr("maru_deep_pro_search.tools.deep_research", _deep_research)
        await tool_deep_research("test", engine="invalid")
        assert called[0]

    @pytest.mark.asyncio
    async def test_cache_hit(self, hit_cache: MagicMock) -> None:
        result = await tool_deep_research("test")
        assert result == "CACHED_RESULT"

    @pytest.mark.asyncio
    async def test_timeout(self, no_cache: None, monkeypatch: Any) -> None:
        async def _deep_research(**_kwargs):
            raise asyncio.TimeoutError()

        monkeypatch.setattr("maru_deep_pro_search.tools.deep_research", _deep_research)
        result = await tool_deep_research("test")
        assert "[TIMEOUT]" in result


# ═══════════════════════════════════════════════════════════════
# tool_answer
# ═══════════════════════════════════════════════════════════════


class TestToolAnswer:
    @pytest.mark.asyncio
    async def test_invalid_engine_fallback(self, no_cache: None, monkeypatch: Any) -> None:
        called = [False]

        async def _deep_research(**kwargs):
            called[0] = True
            assert kwargs["engine"] == "duckduckgo_lite"
            from maru_deep_pro_search.research.deep import ResearchResult

            return ResearchResult(
                query="test",
                engine="duckduckgo_lite",
                total_sources=1,
                sources=[],
            )

        monkeypatch.setattr("maru_deep_pro_search.tools.deep_research", _deep_research)
        await tool_answer("test", engine="invalid")
        assert called[0]

    @pytest.mark.asyncio
    async def test_timeout(self, no_cache: None, monkeypatch: Any) -> None:
        async def _deep_research(**_kwargs):
            raise asyncio.TimeoutError()

        monkeypatch.setattr("maru_deep_pro_search.tools.deep_research", _deep_research)
        result = await tool_answer("test")
        assert "[TIMEOUT]" in result

    @pytest.mark.asyncio
    async def test_no_sources(self, no_cache: None, monkeypatch: Any) -> None:
        async def _deep_research(**_kwargs):
            from maru_deep_pro_search.research.deep import ResearchResult

            return ResearchResult(
                query="test", engine="duckduckgo_lite", total_sources=0, sources=[]
            )

        monkeypatch.setattr("maru_deep_pro_search.tools.deep_research", _deep_research)
        result = await tool_answer("test")
        assert "couldn't find any sources" in result

    @pytest.mark.asyncio
    async def test_with_sources(self, no_cache: None, monkeypatch: Any) -> None:
        from maru_deep_pro_search.research.deep import CitedSource, ResearchResult

        async def _deep_research(**_kwargs):
            return ResearchResult(
                query="test",
                engine="duckduckgo_lite",
                total_sources=1,
                sources=[
                    CitedSource(
                        title="Answer",
                        url="https://example.com",
                        snippet="The answer is 42",
                        citation_id=1,
                    )
                ],
            )

        monkeypatch.setattr("maru_deep_pro_search.tools.deep_research", _deep_research)
        result = await tool_answer("test")
        # format_for_llm output should contain the source
        assert "Answer" in result or "example.com" in result


# ═══════════════════════════════════════════════════════════════
# tool_search_with_citations
# ═══════════════════════════════════════════════════════════════


class TestToolSearchWithCitations:
    @pytest.mark.asyncio
    async def test_invalid_engine_fallback(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.return_value = [
            SearchResult(title="T", url="https://example.com", snippet="S")
        ]
        result = await tool_search_with_citations("test", engine="invalid")
        assert "Citation Search:" in result

    @pytest.mark.asyncio
    async def test_timeout(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.side_effect = asyncio.TimeoutError()
        result = await tool_search_with_citations("test")
        assert "[TIMEOUT]" in result

    @pytest.mark.asyncio
    async def test_maru_search_error_with_fallback(
        self, mock_engine: MagicMock, no_cache: None
    ) -> None:
        fallback_engine = MagicMock()
        fallback_engine.search = AsyncMock(
            return_value=[SearchResult(title="FB", url="https://fb.com", snippet="s")]
        )

        async def _side_effect(*_args, **_kwargs):
            raise MaruSearchError("fail", suggested_engine="bing")

        mock_engine.search.side_effect = _side_effect

        call_count = [0]

        def _create(name):
            if name == "bing":
                call_count[0] += 1
                return fallback_engine
            return mock_engine

        with patch("maru_deep_pro_search.tools.SearchEngineRegistry.create", _create):
            result = await tool_search_with_citations("test")
        assert "FB" in result

    @pytest.mark.asyncio
    async def test_maru_search_error_no_suggested_engine(
        self, mock_engine: MagicMock, no_cache: None
    ) -> None:
        async def _side_effect(*_args, **_kwargs):
            raise MaruSearchError("fail")

        mock_engine.search.side_effect = _side_effect
        with pytest.raises(MaruSearchError):
            await tool_search_with_citations("test")

    @pytest.mark.asyncio
    async def test_source_type_badge(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.return_value = [
            SearchResult(
                title="T",
                url="https://example.com",
                snippet="S",
                source_type=SourceType.GITHUB_REPO,
            )
        ]
        result = await tool_search_with_citations("test")
        assert "[GITHUB-REPO]" in result

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.return_value = []
        result = await tool_search_with_citations("test")
        assert "No results found" in result

    @pytest.mark.asyncio
    async def test_snippet_present(self, mock_engine: MagicMock, no_cache: None) -> None:
        mock_engine.search.return_value = [
            SearchResult(
                title="T",
                url="https://example.com",
                snippet="A longer snippet that should be truncated" * 10,
            )
        ]
        result = await tool_search_with_citations("test")
        assert "A longer snippet" in result


# ═══════════════════════════════════════════════════════════════
# tool_stealthy_fetch
# ═══════════════════════════════════════════════════════════════


class TestToolStealthyFetch:
    @pytest.mark.asyncio
    async def test_delegates_to_fetch_page(self, mock_engine: MagicMock, no_cache: None) -> None:
        result = await tool_stealthy_fetch("https://example.com", max_tokens=3000)
        assert "Example" in result


# ═══════════════════════════════════════════════════════════════
# tool_parallel_search
# ═══════════════════════════════════════════════════════════════


class TestToolParallelSearch:
    @pytest.mark.asyncio
    async def test_invalid_engine_fallback(self, no_cache: None, monkeypatch: Any) -> None:
        async def _web_search(*args, **kwargs):
            return f"Search: test engine={kwargs.get('engine', 'unknown')}"

        monkeypatch.setattr(
            "maru_deep_pro_search.tools.tool_web_search",
            _web_search,
        )
        result = await tool_parallel_search(["q1"], engine="invalid")
        assert "duckduckgo_lite" in result

    @pytest.mark.asyncio
    async def test_exception_in_search(self, no_cache: None, monkeypatch: Any) -> None:
        async def _web_search(*args, **kwargs):
            raise RuntimeError("search boom")

        monkeypatch.setattr("maru_deep_pro_search.tools.tool_web_search", _web_search)
        result = await tool_parallel_search(["q1"])
        assert "Search failed" in result
        assert "search boom" in result

    @pytest.mark.asyncio
    async def test_comparison_mode_url_fallback(self, no_cache: None, monkeypatch: Any) -> None:
        """When no title is found but URL exists, urlparse fallback is used."""
        raw = "Search: test\n   https://docs.python.org/3\n"

        async def _web_search(*args, **kwargs):
            return raw

        monkeypatch.setattr(
            "maru_deep_pro_search.tools.tool_web_search",
            _web_search,
        )
        result = await tool_parallel_search(["q1"], engine="duckduckgo_lite", comparison_mode=True)
        assert "docs.python.org" in result

    @pytest.mark.asyncio
    async def test_comparison_mode_no_title_no_url(self, no_cache: None, monkeypatch: Any) -> None:
        """When neither title nor URL is found, '(no title)' fallback is used."""
        raw = "Search: test\n"

        async def _web_search(*args, **kwargs):
            return raw

        monkeypatch.setattr(
            "maru_deep_pro_search.tools.tool_web_search",
            _web_search,
        )
        result = await tool_parallel_search(["q1"], engine="duckduckgo_lite", comparison_mode=True)
        assert "(no title)" in result

    @pytest.mark.asyncio
    async def test_comparison_mode_full_parse(self, no_cache: None, monkeypatch: Any) -> None:
        """Exercise citation renumbering, title/type/primary extraction."""
        raw = (
            "Search: test\n"
            "1. **My Title** [1] [OFFICIAL-DOCS] [PRIMARY]\n"
            "   https://docs.python.org/3\n"
            "   > snippet here\n"
        )

        async def _web_search(*args, **kwargs):
            return raw

        monkeypatch.setattr(
            "maru_deep_pro_search.tools.tool_web_search",
            _web_search,
        )
        result = await tool_parallel_search(["q1"], engine="duckduckgo_lite", comparison_mode=True)
        assert "My Title" in result
        assert "[OFFICIAL-DOCS]" in result
        assert "✓" in result



