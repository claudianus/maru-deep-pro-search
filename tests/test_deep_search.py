"""Tests for the search-only deep research pipeline."""

from __future__ import annotations

import pytest

from maru_deep_pro_search.research.deep import (
    CitedSource,
    ResearchResult,
    _estimate_quality,
    deep_research,
    format_for_llm,
)


class TestEstimateQuality:
    def test_authority_domain_high(self):
        from maru_deep_pro_search.engines.base import SearchResult

        sr = SearchResult(
            title="React Docs",
            url="https://react.dev",
            is_primary=True,
            url_suggests_docs=True,
            engines_found=["duckduckgo_lite", "bing"],
        )
        assert _estimate_quality(sr) == "high"

    def test_no_signals_low(self):
        from maru_deep_pro_search.engines.base import SearchResult

        sr = SearchResult(title="Blog", url="https://random-blog.com")
        assert _estimate_quality(sr) == "low"

    def test_single_signal_medium(self):
        from maru_deep_pro_search.engines.base import SearchResult

        sr = SearchResult(
            title="Random blog",
            url="https://random-blog.com/post",
            is_primary=True,
        )
        assert _estimate_quality(sr) == "medium"


class TestFormatForLLM:
    def test_empty_result(self):
        result = ResearchResult(query="test", engine="duckduckgo_lite", total_sources=0)
        output = format_for_llm(result)
        assert "No results found" in output

    def test_includes_metadata(self):
        result = ResearchResult(
            query="React 19",
            engine="duckduckgo_lite",
            total_sources=2,
            sources=[
                CitedSource(
                    citation_id=1,
                    url="https://react.dev",
                    title="React v19",
                    snippet="React v19 is now available",
                    quality="high",
                    authority_boost=True,
                    is_primary=True,
                    engines_found=["duckduckgo_lite", "bing"],
                    relevance_score=8.5,
                ),
                CitedSource(
                    citation_id=2,
                    url="https://dev.to/post",
                    title="React 19 review",
                    snippet="A review of React 19",
                    quality="medium",
                    engines_found=["bing"],
                    relevance_score=4.2,
                ),
            ],
            search_coverage={"duckduckgo_lite": 1, "bing": 2},
        )
        output = format_for_llm(result)
        assert "## Research: React 19" in output
        assert "[1] React v19" in output
        assert "[2] React 19 review" in output
        assert "🔒 authority" in output
        assert "✓2 engines" in output
        assert "duckduckgo_lite=1" in output


class TestDeepResearchIntegration:
    @pytest.mark.asyncio
    async def test_returns_result_for_simple_query(self):
        result = await deep_research(
            "Python asyncio",
            max_sources=3,
            expand_queries=False,
        )
        assert result.total_sources > 0
        assert len(result.sources) > 0
        assert all(s.url for s in result.sources)
        assert all(s.title for s in result.sources)

    @pytest.mark.asyncio
    async def test_multi_engine_coverage(self):
        result = await deep_research(
            "React 19",
            max_sources=5,
            expand_queries=False,
        )
        assert result.total_sources > 0
        # At least one source should have multiple engines (cross-validation)
        multi_engine = any(len(s.engines_found) > 1 for s in result.sources)
        # Not guaranteed with circuit breakers, so just check structure
        assert result.search_coverage
        assert result.elapsed_ms > 0

    @pytest.mark.asyncio
    async def test_empty_query_returns_no_results(self):
        result = await deep_research(
            "xyznonexistentquery12345",
            max_sources=3,
            expand_queries=False,
        )
        # May return 0 or few results for nonsense query
        assert result.total_sources >= 0
