"""Tests for extraction utilities."""

from maru_deep_pro_search.extraction.content import truncate_for_llm
from maru_deep_pro_search.utils.url import deduplicate_urls, should_skip_url


class TestTruncateForLlm:
    def test_short_text_passes_through(self):
        text = "hello world"
        assert truncate_for_llm(text, 100) == text

    def test_long_text_truncated(self):
        text = "x " * 500
        result = truncate_for_llm(text, 50)
        assert len(result) < len(text)
        assert "...[truncated]" in result

    def test_empty_text(self):
        assert truncate_for_llm("", 100) == ""

    def test_markdown_preserved(self):
        text = "# Heading\n\nParagraph text.\n\n```python\ncode\n```"
        result = truncate_for_llm(text, 500)
        assert "# Heading" in result


class TestSkipUrl:
    def test_skip_social_media(self):
        assert should_skip_url("https://youtube.com/watch?v=123")
        assert should_skip_url("https://instagram.com/p/abc")
        assert should_skip_url("https://facebook.com/user/posts")
        assert should_skip_url("https://twitter.com/user/status/123")
        assert should_skip_url("https://x.com/user/status/123")
        assert should_skip_url("https://tiktok.com/@user/video/123")
        assert should_skip_url("https://pinterest.com/pin/123")
        assert should_skip_url("https://reddit.com/r/python/comments/123")
        assert should_skip_url("https://linkedin.com/in/user")

    def test_skip_login_pages(self):
        assert should_skip_url("https://example.com/login")
        assert should_skip_url("https://example.com/signup")
        assert should_skip_url("https://example.com/auth/google")

    def test_allow_valid_urls(self):
        assert not should_skip_url("https://docs.python.org/3/library/asyncio.html")
        assert not should_skip_url("https://realpython.com/async-io-python/")
        assert not should_skip_url("https://github.com/python/cpython")
        assert not should_skip_url("https://stackoverflow.com/questions/123")

    def test_skip_tracking_urls(self):
        # Tracking params are stripped by normalize_url, not skipped
        assert not should_skip_url("https://example.com?utm_source=google")
        assert not should_skip_url("https://example.com#comments")


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


class TestExtractCodeBlocks:
    def test_extract_python_block(self):
        from maru_deep_pro_search.extraction.content import extract_code_blocks
        md = "```python\nprint('hello')\n```"
        blocks = extract_code_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert "print('hello')" in blocks[0]["code"]

    def test_extract_no_language(self):
        from maru_deep_pro_search.extraction.content import extract_code_blocks
        md = "```\nsome text\n```"
        blocks = extract_code_blocks(md)
        assert blocks[0]["language"] == "text"

    def test_multiple_blocks(self):
        from maru_deep_pro_search.extraction.content import extract_code_blocks
        md = "```python\na = 1\n```\n\n```js\nconst x = 1;\n```"
        blocks = extract_code_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert blocks[1]["language"] == "js"

    def test_no_blocks(self):
        from maru_deep_pro_search.extraction.content import extract_code_blocks
        assert extract_code_blocks("just text") == []


class TestExtractHeadings:
    def test_extract_h1(self):
        from maru_deep_pro_search.extraction.content import extract_headings
        headings = extract_headings("# Title\n\n## Subtitle")
        assert len(headings) == 2
        assert headings[0] == {"level": 1, "text": "Title"}
        assert headings[1] == {"level": 2, "text": "Subtitle"}

    def test_no_headings(self):
        from maru_deep_pro_search.extraction.content import extract_headings
        assert extract_headings("plain text") == []

    def test_h6_max(self):
        from maru_deep_pro_search.extraction.content import extract_headings
        headings = extract_headings("###### Deep")
        assert headings[0]["level"] == 6


class TestEstimateTokenCount:
    def test_empty(self):
        from maru_deep_pro_search.extraction.content import estimate_token_count
        assert estimate_token_count("") == 0

    def test_approximate(self):
        from maru_deep_pro_search.extraction.content import estimate_token_count
        assert estimate_token_count("abcd") == 1
        assert estimate_token_count("abcdefgh") == 2


class TestTruncateForLlmExtra:
    def test_paragraph_boundary(self):
        from maru_deep_pro_search.extraction.content import truncate_for_llm
        # Paragraph break after 70%+ of max_chars
        text = "word " * 35 + "\n\n" + "more words " * 50
        result = truncate_for_llm(text, max_tokens=50)
        assert "...[truncated]" in result
        assert "more words" not in result

    def test_sentence_boundary(self):
        from maru_deep_pro_search.extraction.content import truncate_for_llm
        # Create text where a sentence boundary exists after 70%+ of max_chars
        text = "First sentence. " * 100 + "Last sentence here."
        result = truncate_for_llm(text, max_tokens=50)
        assert "...[truncated]" in result
        assert "Last sentence here" not in result

    def test_fallback_no_boundary(self):
        from maru_deep_pro_search.extraction.content import truncate_for_llm
        # Long text with no good boundaries (no paragraphs, sentences, or spaces near cutoff)
        text = "a" * 5000
        result = truncate_for_llm(text, max_tokens=50)
        assert "...[truncated]" in result
