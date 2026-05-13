"""Tests for locale-aware query optimization harness."""

from maru_deep_pro_search.utils.locale_harness import (
    get_locale_hint,
    optimize_for_engine,
)


class TestLocaleHarness:
    def test_baidu_english_query_gets_localized(self):
        result = optimize_for_engine("python asyncio tutorial", "baidu")
        assert "教程" in result

    def test_baidu_chinese_query_unchanged(self):
        result = optimize_for_engine("python asyncio 教程", "baidu")
        assert result == "python asyncio 教程"

    def test_naver_english_query_gets_localized(self):
        result = optimize_for_engine("python asyncio tutorial", "naver")
        assert "튜토리얼" in result or "강의" in result

    def test_naver_korean_query_unchanged(self):
        result = optimize_for_engine("python asyncio 강의", "naver")
        assert result == "python asyncio 강의"

    def test_non_locale_engine_unchanged(self):
        result = optimize_for_engine("python asyncio tutorial", "google")
        assert result == "python asyncio tutorial"

    def test_tech_term_replacement_baidu(self):
        result = optimize_for_engine("django documentation", "baidu")
        assert "文档" in result

    def test_tech_term_replacement_naver(self):
        result = optimize_for_engine("django documentation", "naver")
        assert "문서" in result

    def test_get_locale_hint(self):
        assert "Chinese" in get_locale_hint("baidu")
        assert "Korean" in get_locale_hint("naver")
        assert get_locale_hint("google") == "English"
