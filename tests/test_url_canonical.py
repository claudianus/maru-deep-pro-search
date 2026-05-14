"""Tests for canonical URL resolution and redirect handling."""

from __future__ import annotations

from maru_deep_pro_search.utils.url import (
    classify_source_type,
    is_primary_source,
    resolve_canonical_url,
    resolve_redirect,
)


class TestResolveRedirect:
    def test_google_redirect(self):
        url = "/url?q=https%3A%2F%2Fexample.com%2Fpath"
        assert resolve_redirect(url, "https://google.com") == "https://example.com/path"

    def test_google_redirect_with_url_param(self):
        url = "/url?sa=t&url=https%3A%2F%2Fgithub.com%2Fuser%2Frepo"
        assert resolve_redirect(url, "https://google.com") == "https://github.com/user/repo"

    def test_duckduckgo_redirect(self):
        url = "https://r.duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com"
        assert resolve_redirect(url, "https://duckduckgo.com") == "https://example.com"

    def test_duckduckgo_redirect_variant(self):
        url = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fgithub.com%2Ftest"
        assert resolve_redirect(url, "https://duckduckgo.com") == "https://github.com/test"

    def test_bing_redirect(self):
        # Base64 encoded "https://example.com"
        url = "/ck/a?u=a1aHR0cHM6Ly9leGFtcGxlLmNvbQ"
        result = resolve_redirect(url, "https://bing.com")
        assert result == "https://example.com"

    def test_yahoo_redirect(self):
        url = "https://r.search.yahoo.com/_ylt=.../RU=https%3A%2F%2Fexample.com/RV=..."
        assert resolve_redirect(url, "https://yahoo.com") == "https://example.com"

    def test_relative_url(self):
        url = "/path/to/page"
        assert resolve_redirect(url, "https://example.com") == "https://example.com/path/to/page"

    def test_no_redirect_returns_original(self):
        url = "https://example.com/article"
        assert resolve_redirect(url, "https://google.com") == "https://example.com/article"

    def test_empty_url(self):
        assert resolve_redirect("", "https://google.com") == ""

    def test_bing_base64_decode_failure(self):
        # Invalid base64 payload should fall through to relative URL resolution
        url = "/ck/a?u=!!!INVALID!!!"
        result = resolve_redirect(url, "https://bing.com")
        # Falls through to relative URL join
        assert result == "https://bing.com/ck/a?u=!!!INVALID!!!"

    def test_baidu_redirect(self):
        url = "https://baidu.com/link?url=https%3A%2F%2Fexample.com"
        result = resolve_redirect(url, "https://baidu.com")
        assert result == "https://example.com"

    def test_baidu_search_redirect(self):
        url = "https://baidu.com/s?url=https%3A%2F%2Fexample.com"
        result = resolve_redirect(url, "https://baidu.com")
        assert result == "https://example.com"

    def test_generic_redirect_no_match(self):
        # Generic redirect with non-http target — should return original
        url = "https://example.com/page?redirect=/local/path"
        result = resolve_redirect(url, "https://example.com")
        assert result == url


class TestResolveCanonicalUrl:
    def test_strips_tracking_params(self):
        url = "https://example.com/article?utm_source=email&fbclid=123"
        result = resolve_canonical_url(url)
        assert "utm_source" not in result
        assert "fbclid" not in result

    def test_resolves_redirect_in_url(self):
        url = "https://r.duckduckgo.com/l/?uddg=https%3A%2F%2Fgithub.com%2Ftest"
        result = resolve_canonical_url(url)
        assert result == "https://github.com/test"

    def test_returns_original_for_normal_url(self):
        url = "https://github.com/user/repo"
        assert resolve_canonical_url(url) == "https://github.com/user/repo"

    def test_handles_empty(self):
        assert resolve_canonical_url("") == ""


class TestClassifySourceType:
    def test_github_repo(self):
        assert classify_source_type("https://github.com/user/repo") == "github_repo"

    def test_official_docs(self):
        assert classify_source_type("https://docs.python.org/3/") == "official_docs"

    def test_stackoverflow_forum(self):
        assert classify_source_type("https://stackoverflow.com/questions/123") == "forum"

    def test_arxiv_academic(self):
        assert classify_source_type("https://arxiv.org/abs/1234.5678") == "academic_paper"

    def test_medium_blog(self):
        assert classify_source_type("https://medium.com/@user/article") == "blog_review"

    def test_pypi_registry(self):
        assert classify_source_type("https://pypi.org/project/requests/") == "package_registry"

    def test_tutorial(self):
        assert (
            classify_source_type("https://example.com/guide", snippet="getting started tutorial")
            == "tutorial"
        )

    def test_official_docs_with_pattern(self):
        # docs pattern in primary source domain (e.g., /docs/ or /api/)
        assert classify_source_type("https://react.dev/docs/thinking-in-react") == "official_docs"
        assert classify_source_type("https://fastapi.tiangolo.com/tutorial/") == "official_docs"

    def test_news_classification(self):
        assert classify_source_type("https://news.ycombinator.com/item?id=123") == "news"
        assert classify_source_type("https://techcrunch.com/2024/01/01/article") == "news"

    def test_unknown_fallback(self):
        assert classify_source_type("https://random-site.com/page") == "unknown"


class TestIsPrimarySource:
    def test_github_is_primary(self):
        assert is_primary_source("https://github.com/user/repo") is True

    def test_docs_is_primary(self):
        assert is_primary_source("https://docs.python.org/3/") is True

    def test_stackoverflow_is_primary(self):
        assert is_primary_source("https://stackoverflow.com/q/123") is True

    def test_medium_is_not_primary(self):
        assert is_primary_source("https://medium.com/article") is False

    def test_dev_to_is_not_primary(self):
        assert is_primary_source("https://dev.to/article") is False

    def test_with_source_type_override(self):
        assert is_primary_source("https://example.com", "official_docs") is True
