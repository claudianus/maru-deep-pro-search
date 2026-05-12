"""Tests for Korean source support."""


from maru_deep_pro_search.engines.base import ContentType
from maru_deep_pro_search.engines.base import _guess_content_type
from maru_deep_pro_search.research.expander import _select_angles, expand_query
from maru_deep_pro_search.utils.url import is_authority_domain


class TestKoreanQueryExpansion:
    def test_korean_query_detected(self):
        subqueries = expand_query("파이썬 asyncio 한국", max_subqueries=5)
        assert any("한국" in sq or "국내" in sq for sq in subqueries)

    def test_korean_angles_selected(self):
        angles = _select_angles("한국 개발자 커뮤니티")
        assert "korean_community" in angles
        assert "korean_docs" in angles

    def test_english_query_not_korean(self):
        angles = _select_angles("python asyncio tutorial")
        assert "korean_community" not in angles
        assert any(a.startswith("recent") for a in angles)

    def test_mixed_query_korean_priority(self):
        angles = _select_angles("Korean python developer community")
        assert "korean_community" in angles


class TestKoreanDomains:
    def test_velog_recognized(self):
        assert is_authority_domain("https://velog.io/@user/post")

    def test_tistory_recognized(self):
        assert is_authority_domain("https://user.tistory.com/123")

    def test_naver_recognized(self):
        assert is_authority_domain("https://blog.naver.com/user/123")

    def test_brunch_recognized(self):
        assert is_authority_domain("https://brunch.co.kr/@user/123")

    def test_okky_recognized(self):
        assert is_authority_domain("https://okky.kr/article/123")


class TestKoreanContentType:
    def test_velog_detected_as_article(self):
        result = _guess_content_type("https://velog.io/@user/python-async")
        assert result == ContentType.ARTICLE

    def test_tistory_detected_as_article(self):
        result = _guess_content_type("https://user.tistory.com/123")
        assert result == ContentType.ARTICLE

    def test_naver_blog_detected_as_article(self):
        result = _guess_content_type("https://blog.naver.com/user/123")
        assert result == ContentType.ARTICLE

    def test_brunch_detected_as_article(self):
        result = _guess_content_type("https://brunch.co.kr/@user/123")
        assert result == ContentType.ARTICLE

    def test_okky_detected_as_article(self):
        result = _guess_content_type("https://okky.kr/article/123")
        assert result == ContentType.ARTICLE
