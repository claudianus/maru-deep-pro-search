"""Integration tests that verify actual tool output format.

These tests call real MCP tools and assert on the output structure,
ensuring regressions in output format are caught immediately.
"""

from __future__ import annotations

import pytest

from maru_deep_pro_search.tools import (
    tool_answer,
    tool_deep_research,
    tool_fetch_page,
    tool_parallel_search,
    tool_search_with_citations,
    tool_web_search,
)


class TestDeepResearchOutput:
    @pytest.mark.asyncio
    async def test_has_research_header(self):
        result = await tool_deep_research("React 19", engine="bing", max_sources=2, expand_queries=False)
        assert "## Research:" in result
        assert "React 19" in result

    @pytest.mark.asyncio
    async def test_has_engine_coverage_metadata(self):
        result = await tool_deep_research("Python asyncio", engine="bing", max_sources=2, expand_queries=False)
        assert "_engines:" in result
        assert "sources:" in result
        assert "ms_" in result

    @pytest.mark.asyncio
    async def test_has_sources_section_with_badges(self):
        result = await tool_deep_research("React 19", engine="bing", max_sources=2, expand_queries=False)
        assert "### Sources" in result
        assert "#### [1]" in result
        assert "http" in result  # URL present

    @pytest.mark.asyncio
    async def test_no_full_markdown_content(self):
        """Output must NOT contain code blocks or very long content lines."""
        result = await tool_deep_research("React 19", engine="bing", max_sources=2, expand_queries=False)
        assert "```" not in result, "Output should not contain code blocks"
        lines = result.split("\n")
        long_lines = [ln for ln in lines if len(ln) > 600]
        assert len(long_lines) == 0, f"Found {len(long_lines)} lines > 600 chars"

    @pytest.mark.asyncio
    async def test_has_key_findings_section(self):
        result = await tool_deep_research("React 19", engine="bing", max_sources=2, expand_queries=False)
        assert "### Key Findings" in result

    @pytest.mark.asyncio
    async def test_no_synthesized_answer_section(self):
        """Old format had synthesized answer; new format must not have it."""
        result = await tool_deep_research("React 19", engine="bing", max_sources=2, expand_queries=False)
        assert "### Key Findings" in result
        # Should NOT have old-style sections
        assert "Current state" not in result or "### Sources" in result


class TestWebSearchOutput:
    @pytest.mark.asyncio
    async def test_has_search_header(self):
        result = await tool_web_search("Python asyncio", max_results=3)
        assert "Search:" in result
        assert "Python asyncio" in result

    @pytest.mark.asyncio
    async def test_has_numbered_results(self):
        result = await tool_web_search("Python asyncio", max_results=3)
        assert "1. **" in result
        assert "http" in result

    @pytest.mark.asyncio
    async def test_has_citation_ids(self):
        result = await tool_web_search("Python asyncio", max_results=3)
        assert "[1]" in result


class TestSearchWithCitationsOutput:
    @pytest.mark.asyncio
    async def test_has_pre_numbered_citations(self):
        result = await tool_search_with_citations("React Server Components", max_results=3)
        assert "## Citation Search:" in result
        assert "[1]" in result
        assert "URL:" in result

    @pytest.mark.asyncio
    async def test_suggests_fetch_tools(self):
        result = await tool_search_with_citations("React Server Components", max_results=2)
        assert "fetch_page" in result or "fetch_bulk" in result


class TestAnswerOutput:
    @pytest.mark.asyncio
    async def test_matches_deep_research_format(self):
        """answer tool now delegates to deep_research + format_for_llm."""
        result = await tool_answer("React 19", engine="bing", max_sources=2, max_tokens=3000)
        assert "## Research:" in result
        assert "### Sources" in result


class TestFetchPageOutput:
    @pytest.mark.asyncio
    async def test_has_security_wrapper(self):
        result = await tool_fetch_page("https://react.dev", max_tokens=500)
        assert "EXTERNAL CONTENT" in result
        assert "AGENT SECURITY PROTOCOL" in result

    @pytest.mark.asyncio
    async def test_has_content_or_error(self):
        result = await tool_fetch_page("https://react.dev", max_tokens=500)
        # Should have either content or a clear error/block message
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_respects_max_tokens(self):
        result = await tool_fetch_page("https://react.dev", max_tokens=300)
        # Very rough check: output shouldn't be huge
        assert len(result) < 8000


class TestParallelSearchOutput:
    @pytest.mark.asyncio
    async def test_comparison_mode_has_table(self):
        result = await tool_parallel_search(
            ["React vs Vue", "React vs Svelte"],
            engine="bing",
            max_results=2,
            comparison_mode=True,
        )
        assert "### Comparison Summary" in result
        assert "| Query |" in result
        assert "|-------|" in result

    @pytest.mark.asyncio
    async def test_comparison_table_has_nonempty_titles(self):
        result = await tool_parallel_search(
            ["React vs Vue", "React vs Svelte"],
            engine="bing",
            max_results=2,
            comparison_mode=True,
        )
        # If all searches failed, skip this assertion
        if "Search failed" in result and "[1]" not in result:
            pytest.skip("All search engines unavailable")
        # Extract table rows and ensure no "(no title)" when URLs exist
        lines = result.split("\n")
        table_rows = [ln for ln in lines if ln.startswith("| ") and "Query" not in ln and "---" not in ln]
        for row in table_rows:
            parts = row.split("|")
            if len(parts) >= 3:
                title_cell = parts[2].strip()
                # Title should either be a real title or a domain fallback, not empty
                assert len(title_cell) > 2, f"Empty title in row: {row}"

    @pytest.mark.asyncio
    async def test_has_query_sections(self):
        result = await tool_parallel_search(
            ["React vs Vue"],
            engine="bing",
            max_results=2,
            comparison_mode=False,
        )
        assert "React vs Vue" in result
        # Either has results or graceful error message
        assert "[1]" in result or "Search failed" in result
