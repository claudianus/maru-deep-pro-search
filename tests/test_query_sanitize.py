"""Tests for query_sanitize — stale year removal."""

from maru_deep_pro_search.utils.query_sanitize import sanitize_query


class TestSanitizeQuery:
    def test_no_change_for_current_year(self):
        assert (
            sanitize_query("Python 3.13 features 2026", current_year=2026)
            == "Python 3.13 features 2026"
        )

    def test_replaces_single_stale_year(self):
        assert (
            sanitize_query("React best practices 2024", current_year=2026)
            == "React best practices 2026"
        )

    def test_replaces_stale_year_range(self):
        result = sanitize_query("AI regulation 2024 2025", current_year=2026)
        assert "2024" not in result
        assert "2025" not in result
        assert "2026" in result

    def test_replaces_in_phrase(self):
        result = sanitize_query("Python features in 2024", current_year=2026)
        assert "2024" not in result
        assert "in 2026" in result

    def test_keeps_versions_in_comparison(self):
        result = sanitize_query("Next.js 14 vs 15 2023", current_year=2026)
        assert "14 vs 15" in result
        assert "2023" not in result

    def test_multiple_stale_years(self):
        result = sanitize_query("History of AI 2022 2023 2024", current_year=2026)
        assert "2022" not in result
        assert "2023" not in result
        assert "2024" not in result

    def test_empty_query(self):
        assert sanitize_query("") == ""

    def test_no_year_query(self):
        assert sanitize_query("Python asyncio tutorial") == "Python asyncio tutorial"

    def test_as_of_phrase(self):
        result = sanitize_query("Status as of 2024", current_year=2026)
        assert "2024" not in result
        assert "as of 2026" in result

    def test_dedupes_current_year(self):
        result = sanitize_query("React 2025 2024", current_year=2026)
        # Should not produce duplicate current year
        assert "2026 2026" not in result

    def test_future_year_unchanged(self):
        result = sanitize_query("AI trends 2028", current_year=2026)
        assert "2028" in result

    def test_sanitize_queries_list(self):
        from maru_deep_pro_search.utils.query_sanitize import sanitize_queries
        queries = ["React 2024", "Python 2025"]
        results = sanitize_queries(queries, current_year=2026)
        assert results[0] == "React 2026"
        assert "2025" not in results[1]

    def test_whitespace_only_query(self):
        assert sanitize_query("   ") == "   "

    def test_defensive_future_year_in_match(self, monkeypatch):
        import re

        from maru_deep_pro_search.utils import query_sanitize
        # Patch the stale pattern to include a future year so the defensive
        # check in _replace_year is exercised.
        original_pattern = query_sanitize._stale_year_pattern

        def fake_pattern(year):
            return re.compile(r"\b(2024|2028)\b")

        monkeypatch.setattr(query_sanitize, "_stale_year_pattern", fake_pattern)
        result = sanitize_query("AI 2028", current_year=2026)
        assert "2028" in result
