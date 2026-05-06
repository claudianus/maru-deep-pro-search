"""Tests for extractor utilities."""

import pytest
from clco_deep_research.research.extractor import (
    truncate_for_llm,
    skip_url,
    deduplicate_urls,
)


class TestTruncateForLlm:
    def test_short_text_passes_through(self):
        text = "hello world"
        assert truncate_for_llm(text, 100) == text

    def test_long_text_truncated(self):
        text = "x " * 500
        result = truncate_for_llm(text, 50)
        assert len(result) < len(text)
        assert result.endswith("...")

    def test_empty_text(self):
        assert truncate_for_llm("", 100) == ""

    def test_markdown_preserved(self):
        text = "# Heading\n\nParagraph text.\n\n```python\ncode\n```"
        result = truncate_for_llm(text, 500)
        assert "# Heading" in result


class TestSkipUrl:
    def test_skip_social_media(self):
        assert skip_url("https://youtube.com/watch?v=123")
        assert skip_url("https://instagram.com/p/abc")
        assert skip_url("https://facebook.com/user/posts")
        assert skip_url("https://twitter.com/user/status/123")
        assert skip_url("https://x.com/user/status/123")
        assert skip_url("https://tiktok.com/@user/video/123")
        assert skip_url("https://pinterest.com/pin/123")
        assert skip_url("https://reddit.com/r/python/comments/123")
        assert skip_url("https://linkedin.com/in/user")

    def test_skip_login_pages(self):
        assert skip_url("https://example.com/login")
        assert skip_url("https://example.com/signup")
        assert skip_url("https://example.com/auth/google")

    def test_allow_valid_urls(self):
        assert not skip_url("https://docs.python.org/3/library/asyncio.html")
        assert not skip_url("https://realpython.com/async-io-python/")
        assert not skip_url("https://github.com/python/cpython")
        assert not skip_url("https://stackoverflow.com/questions/123")

    def test_skip_tracking_urls(self):
        assert skip_url("https://example.com?utm_source=google")
        assert skip_url("https://example.com#comments")


class TestDeduplicateUrls:
    def test_remove_duplicates(self):
        urls = ["https://a.com/", "https://a.com", "https://b.com/"]
        result = deduplicate_urls(urls)
        assert len(result) == 2

    def test_preserve_order(self):
        urls = ["https://c.com", "https://a.com", "https://b.com", "https://a.com/"]
        result = deduplicate_urls(urls)
        assert result == ["https://c.com", "https://a.com", "https://b.com"]

    def test_empty_list(self):
        assert deduplicate_urls([]) == []
