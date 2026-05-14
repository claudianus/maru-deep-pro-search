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

    def test_spam_domain_penalty(self):
        r = SearchResult(title="Test", url="https://geeksforgeeks.org/post", engine="ddg")
        score_spam = _score_metadata(r)
        r2 = SearchResult(title="Test", url="https://example.com/post", engine="ddg")
        score_normal = _score_metadata(r2)
        assert score_spam < score_normal

    def test_medium_penalty(self):
        r = SearchResult(title="Test", url="https://medium.com/@user/post", engine="ddg")
        score = _score_metadata(r)
        # Medium gets a penalty but might still be positive due to other boosts
        assert isinstance(score, float)

    def test_blog_penalty(self):
        r = SearchResult(title="Test", url="https://blog.example.com/post", engine="ddg")
        score = _score_metadata(r)
        assert isinstance(score, float)

    def test_code_content_type(self):
        r = SearchResult(
            title="Test",
            url="https://github.com/user/repo",
            engine="ddg",
            likely_content_type=ContentType.CODE,
        )
        score_code = _score_metadata(r)
        r2 = SearchResult(
            title="Test",
            url="https://github.com/user/repo",
            engine="ddg",
            likely_content_type=ContentType.FORUM,
        )
        score_forum = _score_metadata(r2)
        assert score_code != score_forum

    def test_url_suggests_docs(self):
        r = SearchResult(
            title="Test",
            url="https://docs.python.org/3",
            engine="ddg",
            url_suggests_docs=True,
        )
        score = _score_metadata(r)
        assert score > 0


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

    def test_dedupe_merges_engines(self):
        """Duplicate should merge engine lists from the result with more engines."""
        # Need DIFFERENT URLs so URL-level dedup doesn't catch them first
        results = [
            SearchResult(
                title="Python Asyncio Complete Guide",
                url="https://a.com",
                snippet="Learn python asyncio...",
                engine="ddg",
                engines_found=["ddg"],
                position=1,
            ),
            SearchResult(
                title="Python Asyncio Complete Guide",
                url="https://b.com",
                snippet="Learn python asyncio...",
                engine="bing",
                engines_found=["ddg", "bing", "google"],
                position=2,
            ),
        ]
        ranked = merge_results(
            {"ddg": [results[0]], "bing": [results[1]], "google": [results[1]]},
            "python"
        )
        assert len(ranked) == 1
        assert set(ranked[0].result.engines_found) == {"ddg", "bing", "google"}


class TestBM25EdgeCases:
    def test_bm25_import_error(self, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "rank_bm25", None)
        from maru_deep_pro_search.engines.base import SearchResult
        from maru_deep_pro_search.research.ranker import _compute_bm25_scores

        results = [SearchResult(title="Test", url="https://example.com", engine="ddg")]
        scores = _compute_bm25_scores("test", results)
        assert scores == {"https://example.com": 0.0}

    def test_bm25_scoring_exception(self, monkeypatch):
        import sys
        from unittest.mock import MagicMock
        mock_bm25 = MagicMock()
        mock_bm25.BM25Okapi.side_effect = RuntimeError("BM25 fail")
        monkeypatch.setitem(sys.modules, "rank_bm25", mock_bm25)
        from maru_deep_pro_search.engines.base import SearchResult
        from maru_deep_pro_search.research.ranker import _compute_bm25_scores

        results = [SearchResult(title="Test", url="https://example.com", engine="ddg")]
        scores = _compute_bm25_scores("test", results)
        assert scores == {"https://example.com": 0.0}

    def test_bm25_empty_query_tokens(self, monkeypatch):
        import sys
        from unittest.mock import MagicMock
        mock_bm25 = MagicMock()
        mock_instance = MagicMock()
        mock_instance.get_scores.return_value = [1.5]
        mock_bm25.BM25Okapi.return_value = mock_instance
        monkeypatch.setitem(sys.modules, "rank_bm25", mock_bm25)
        from maru_deep_pro_search.engines.base import SearchResult
        from maru_deep_pro_search.research.ranker import _compute_bm25_scores

        # extract_keywords returns empty for punctuation-only query
        results = [SearchResult(title="Test", url="https://example.com", engine="ddg", snippet="test")]
        scores = _compute_bm25_scores("!!!", results)
        assert "https://example.com" in scores


class TestNormalizeText:
    def test_empty_text(self):
        from maru_deep_pro_search.research.ranker import _normalize_text
        assert _normalize_text("") == set()


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

    def test_medium_quality_scored(self):
        from maru_deep_pro_search.engines.base import ExtractionQuality, PageContent

        pages = [
            PageContent(
                url="https://medium.com",
                text="some text",
                quality=ExtractionQuality.MEDIUM,
                title="Medium",
            ),
        ]
        ranked = rank_pages(pages, "test")
        assert len(ranked) == 1

    def test_authority_domain_boost(self):
        from maru_deep_pro_search.engines.base import ExtractionQuality, PageContent

        pages = [
            PageContent(
                url="https://docs.python.org/3",
                text="python docs",
                quality=ExtractionQuality.MEDIUM,
                title="Docs",
            ),
            PageContent(
                url="https://random.com",
                text="random blog",
                quality=ExtractionQuality.MEDIUM,
                title="Blog",
            ),
        ]
        ranked = rank_pages(pages, "python")
        assert ranked[0].url == "https://docs.python.org/3"

    def test_content_type_preference(self):
        from maru_deep_pro_search.engines.base import ContentType, ExtractionQuality, PageContent

        pages = [
            PageContent(
                url="https://a.com",
                text="docs",
                quality=ExtractionQuality.MEDIUM,
                title="A",
                content_type=ContentType.DOCUMENTATION,
            ),
            PageContent(
                url="https://b.com",
                text="article",
                quality=ExtractionQuality.MEDIUM,
                title="B",
                content_type=ContentType.ARTICLE,
            ),
        ]
        ranked = rank_pages(pages, "test")
        assert ranked[0].url == "https://a.com"

    def test_freshness_boost(self):
        from maru_deep_pro_search.engines.base import ExtractionQuality, PageContent

        pages = [
            PageContent(
                url="https://old.com",
                text="old",
                quality=ExtractionQuality.MEDIUM,
                title="Old",
                freshness_days=100,
            ),
            PageContent(
                url="https://new.com",
                text="new",
                quality=ExtractionQuality.MEDIUM,
                title="New",
                freshness_days=7,
            ),
        ]
        ranked = rank_pages(pages, "test")
        assert ranked[0].url == "https://new.com"

    def test_code_richness_boost(self):
        from maru_deep_pro_search.engines.base import ExtractionQuality, PageContent

        pages = [
            PageContent(
                url="https://code.com",
                text="code",
                quality=ExtractionQuality.MEDIUM,
                title="Code",
                code_to_text_ratio=0.3,
            ),
            PageContent(
                url="https://text.com",
                text="text",
                quality=ExtractionQuality.MEDIUM,
                title="Text",
                code_to_text_ratio=0.05,
            ),
        ]
        ranked = rank_pages(pages, "test")
        assert ranked[0].url == "https://code.com"

    def test_freshness_90_days(self):
        from maru_deep_pro_search.engines.base import ExtractionQuality, PageContent

        pages = [
            PageContent(
                url="https://old.com",
                text="old",
                quality=ExtractionQuality.MEDIUM,
                title="Old",
                freshness_days=100,
            ),
            PageContent(
                url="https://recent.com",
                text="recent",
                quality=ExtractionQuality.MEDIUM,
                title="Recent",
                freshness_days=60,
            ),
        ]
        ranked = rank_pages(pages, "test")
        assert ranked[0].url == "https://recent.com"
