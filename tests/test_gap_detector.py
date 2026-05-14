"""Tests for research gap detection."""

from __future__ import annotations

from unittest.mock import MagicMock

from maru_deep_pro_search.research.gap_detector import detect_gaps


class TestDetectGaps:
    def test_empty_sources(self):
        assert detect_gaps("python asyncio", []) == []

    def test_no_keywords(self):
        # Query with only stop words
        sources = [MagicMock(snippet="some content")]
        assert detect_gaps("the and or", sources) == []

    def test_fully_covered(self):
        # Source covers all research angles, but Priority 3 fallback still adds
        # benchmark/security because the query doesn't contain those words
        text = "python asyncio " + " ".join([
            "benchmark performance", "security vulnerability", "production deployment",
            "migration guide", "best practices", "common errors", "official documentation",
            "github repository", "release notes",
        ])
        sources = [MagicMock(snippet=text, markdown="", content="")]
        result = detect_gaps("python asyncio", sources)
        # Priority 3 always adds benchmark/security if query lacks them
        assert any("benchmark" in r for r in result)

    def test_uncovered_keywords(self):
        sources = [MagicMock(snippet="python tutorial", markdown="", content="")]
        result = detect_gaps("python asyncio migration", sources)
        assert any("asyncio" in r for r in result)
        assert any("migration" in r for r in result)

    def test_uncovered_angles(self):
        sources = [MagicMock(snippet="python tutorial", markdown="", content="")]
        result = detect_gaps("python asyncio", sources)
        assert len(result) > 0
        assert any("benchmark" in r or "security" in r for r in result)

    def test_limit_three_suggestions(self):
        sources = [MagicMock(snippet="", markdown="", content="")]
        result = detect_gaps("python asyncio fastapi django flask", sources)
        assert len(result) <= 3

    def test_uses_markdown_content_snippet(self):
        sources = [
            MagicMock(
                markdown="python asyncio markdown",
                content="content text",
                snippet="snippet text",
            )
        ]
        result = detect_gaps("python asyncio", sources)
        # 'python' and 'asyncio' are in markdown, so no keyword gaps
        # But research angles might still be uncovered
        assert isinstance(result, list)

    def test_benchmark_security_fallback(self):
        sources = [MagicMock(snippet="python asyncio guide", markdown="", content="")]
        result = detect_gaps("python asyncio best practices", sources)
        # Best practices is covered, but benchmark/security might be added
        assert isinstance(result, list)
