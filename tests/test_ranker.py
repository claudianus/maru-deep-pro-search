"""Tests for intelligent ranking engine."""

from maru_deep_pro_search.engines.base import ContentType, SearchResult
from maru_deep_pro_search.research.ranker import (
    _score_metadata,
    merge_results,
    rank_pages,
)


class TestScoreMetadata:
    def test_authority_boost(self):
        r = SearchResult(title="Test", url="https://docs.python.org/3/tutorial", engine="ddg")
        score = _score_metadata(r)
        assert score > 0

    def test_docs_type_boost(self):
        r = SearchResult(
            title="Test",
            url="https://example.com/docs",
            engine="ddg",
            likely_content_type=ContentType.DOCUMENTATION,
        )
        r2 = SearchResult(
            title="Test",
            url="https://example.com/blog",
            engine="ddg",
            likely_content_type=ContentType.ARTICLE,
        )
        assert _score_metadata(r) > _score_metadata(r2)

    def test_cross_engine_boost(self):
        r = SearchResult(title="Test", url="https://example.com", engine="ddg")
        r.engines_found = ["ddg", "google"]
        r.cross_engine_score = 1.0
        score_multi = _score_metadata(r)

        r2 = SearchResult(title="Test", url="https://example.com", engine="ddg")
        r2.engines_found = ["ddg"]
        score_single = _score_metadata(r2)

        assert score_multi > score_single


class TestMergeResults:
    def test_single_engine_ranking(self):
        results = [
            SearchResult(
                title="A",
                url="https://a.com",
                snippet="python asyncio guide",
                engine="ddg",
                position=1,
            ),
            SearchResult(
                title="B",
                url="https://b.com",
                snippet="python threading docs",
                engine="ddg",
                position=2,
            ),
        ]
        ranked = merge_results({"ddg": results}, "python asyncio")
        assert len(ranked) == 2
        assert ranked[0].citation_id == 1
        assert ranked[1].citation_id == 2

    def test_deduplication(self):
        results1 = [
            SearchResult(title="A", url="https://a.com", engine="ddg"),
        ]
        results2 = [
            SearchResult(title="A", url="https://a.com/", engine="google"),
        ]
        ranked = merge_results({"ddg": results1, "google": results2}, "test")
        assert len(ranked) == 1
        assert len(ranked[0].result.engines_found) == 2

    def test_empty_results(self):
        ranked = merge_results({}, "test")
        assert ranked == []

    def test_fuzzy_dedupe_by_title(self):
        """Same content on different URLs should be deduped by title similarity."""
        results = [
            SearchResult(
                title="Python Asyncio Complete Guide",
                url="https://realpython.com/asyncio",
                snippet="Learn asyncio...",
                engine="ddg",
            ),
            SearchResult(
                title="Python Asyncio Complete Guide",
                url="https://medium.com/mirror/asyncio",
                snippet="Learn asyncio...",
                engine="bing",
            ),
            SearchResult(
                title="Different Approach to Async",
                url="https://other.com/async",
                snippet="Alternative...",
                engine="ddg",
            ),
        ]
        ranked = merge_results({"ddg": results[:2], "bing": results[2:]}, "python asyncio")
        # Should dedupe the two identical titles, keep the distinct one
        assert len(ranked) == 2

    def test_fuzzy_dedupe_by_snippet(self):
        """Same snippet on different URLs should be deduped."""
        results = [
            SearchResult(
                title="Guide A",
                url="https://a.com",
                snippet="This is the exact same tutorial content about python asyncio for beginners",
                engine="ddg",
            ),
            SearchResult(
                title="Guide B",
                url="https://b.com",
                snippet="This is the exact same tutorial content about python asyncio for beginners",
                engine="searxng",
            ),
        ]
        ranked = merge_results({"ddg": [results[0]], "searxng": [results[1]]}, "python asyncio")
        assert len(ranked) == 1

    def test_fuzzy_dedupe_keeps_distinct(self):
        """Truly different results should NOT be deduped."""
        results = [
            SearchResult(
                title="FastAPI Tutorial",
                url="https://fastapi.tiangolo.com",
                snippet="Build APIs with FastAPI...",
                engine="ddg",
            ),
            SearchResult(
                title="Django REST Framework",
                url="https://django-rest-framework.org",
                snippet="Build APIs with DRF...",
                engine="bing",
            ),
        ]
        ranked = merge_results({"ddg": [results[0]], "bing": [results[1]]}, "python web framework")
        assert len(ranked) == 2


class TestSemanticRanker:
    def test_available_returns_bool(self):
        from maru_deep_pro_search.research.semantic_ranker import SemanticRanker

        result = SemanticRanker.available()
        assert isinstance(result, bool)

    def test_score_results_empty(self):
        from maru_deep_pro_search.research.semantic_ranker import SemanticRanker

        scores = SemanticRanker.score_results("test", [])
        assert scores == []

    def test_sentence_similarity_empty(self):
        from maru_deep_pro_search.research.semantic_ranker import SemanticRanker

        result = SemanticRanker.sentence_similarity([])
        assert result == []

    def test_semantic_dedupe_empty(self):
        from maru_deep_pro_search.research.semantic_ranker import SemanticRanker

        result = SemanticRanker.semantic_dedupe([])
        assert result == []


class TestRankPages:
    def test_empty_list(self):
        assert rank_pages([], "test") == []

    def test_quality_preference(self):
        from maru_deep_pro_search.engines.base import ExtractionQuality, PageContent

        pages = [
            PageContent(
                url="https://low.com", text="some text", quality=ExtractionQuality.LOW, title="Low"
            ),
            PageContent(
                url="https://high.com",
                text="some text",
                quality=ExtractionQuality.HIGH,
                title="High",
            ),
        ]
        ranked = rank_pages(pages, "test")
        assert ranked[0].quality == ExtractionQuality.HIGH
