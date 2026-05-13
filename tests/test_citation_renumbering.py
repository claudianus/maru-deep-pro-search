"""Tests for stable citation ID numbering."""

from __future__ import annotations

from maru_deep_pro_search.research.deep import CitedSource, ResearchResult, format_for_llm


class TestCitationNumbering:
    def test_sequential_ids(self):
        """Sources should have sequential citation IDs."""
        sources = [
            CitedSource(citation_id=1, url="http://a.com", title="A", quality="high"),
            CitedSource(citation_id=2, url="http://b.com", title="B", quality="high"),
        ]
        ids = [s.citation_id for s in sources]
        assert ids == [1, 2]

    def test_format_for_llm_uses_sequential_ids(self):
        result = ResearchResult(
            query="test",
            engine="duckduckgo_lite",
            total_sources=2,
            sources=[
                CitedSource(
                    citation_id=1,
                    url="http://a.com",
                    title="A",
                    quality="high",
                    snippet="content A",
                ),
                CitedSource(
                    citation_id=2,
                    url="http://b.com",
                    title="B",
                    quality="high",
                    snippet="content B",
                ),
            ],
        )
        output = format_for_llm(result)
        assert "[1]" in output
        assert "[2]" in output
        assert "#### [1] A" in output
        assert "#### [2] B" in output
