"""Tests for search engine registry and multi-engine support."""

import pytest

from maru_deep_pro_search.engines.registry import SearchEngineRegistry


class TestSearchEngineRegistry:
    def test_all_engines_registered(self):
        engines = SearchEngineRegistry.list_engines()
        assert "duckduckgo" in engines
        assert "duckduckgo_lite" in engines
        assert "bing" in engines
        assert "naver" in engines
        assert "google" in engines
        assert "startpage" in engines
        assert "yahoo" in engines
        assert "ecosia" in engines
        assert "bing" in engines
        assert len(engines) >= 8

    def test_create_duckduckgo(self):
        engine = SearchEngineRegistry.create("duckduckgo")
        assert engine.name == "duckduckgo"

    def test_create_duckduckgo_lite(self):
        engine = SearchEngineRegistry.create("duckduckgo_lite")
        assert engine.name == "duckduckgo"

    def test_create_bing(self):
        engine = SearchEngineRegistry.create("bing")
        assert engine.name == "bing"

    def test_create_naver(self):
        engine = SearchEngineRegistry.create("naver")
        assert engine.name == "naver"

    def test_create_google(self):
        engine = SearchEngineRegistry.create("google")
        assert engine.name == "google"

    def test_create_startpage(self):
        engine = SearchEngineRegistry.create("startpage")
        assert engine.name == "startpage"

    def test_create_yahoo(self):
        engine = SearchEngineRegistry.create("yahoo")
        assert engine.name == "yahoo"

    def test_create_ecosia(self):
        engine = SearchEngineRegistry.create("ecosia")
        assert engine.name == "ecosia"

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            SearchEngineRegistry.create("nonexistent")

    def test_create_baidu(self):
        engine = SearchEngineRegistry.create("baidu")
        assert engine.name == "baidu"

    def test_is_registered(self):
        assert SearchEngineRegistry.is_registered("bing")
        assert SearchEngineRegistry.is_registered("google")
        assert SearchEngineRegistry.is_registered("startpage")
        assert SearchEngineRegistry.is_registered("yahoo")
        assert SearchEngineRegistry.is_registered("ecosia")
        assert SearchEngineRegistry.is_registered("baidu")
        assert not SearchEngineRegistry.is_registered("nonexistent")

    def test_all_engines_have_parent_initialized_attrs(self):
        """INHERIT-3/5: Every SearchEngine subclass must inherit parent __init__ state.

        Regression guard: subclasses that override __init__ without calling
        super().__init__() silently break _circuit_breaker and _last_request_time,
        which crashes at runtime when __init_subclass__ wraps search().
        """
        for name in SearchEngineRegistry.list_engines():
            engine = SearchEngineRegistry.create(name)
            assert hasattr(engine, "_circuit_breaker"), (
                f"{name}: missing _circuit_breaker — did __init__ forget super().__init__()?"
            )
            assert hasattr(engine, "_last_request_time"), (
                f"{name}: missing _last_request_time — did __init__ forget super().__init__()?"
            )

    def test_recommend_engines(self):
        engines = SearchEngineRegistry.recommend_engines("python asyncio", count=3)
        assert isinstance(engines, list)
        assert len(engines) <= 3

    def test_recommend_engines_handles_exception(self, monkeypatch):
        original_create = SearchEngineRegistry.create
        monkeypatch.setattr(
            SearchEngineRegistry,
            "create",
            lambda name: (_ for _ in ()).throw(RuntimeError("fail")) if name == "duckduckgo" else original_create(name),
        )
        engines = SearchEngineRegistry.recommend_engines("test", count=5)
        assert isinstance(engines, list)


class TestBaseEngine:
    @pytest.mark.asyncio
    async def test_cooldown_wait(self):
        from maru_deep_pro_search.engines.base import SearchEngine
        engine = SearchEngineRegistry.create("duckduckgo")
        engine.min_request_interval = 0.1
        engine._last_request_time = 0
        await engine._ensure_cooldown()
        # Second call should wait
        engine._last_request_time = __import__("time").monotonic()
        start = __import__("time").monotonic()
        await engine._ensure_cooldown()
        assert __import__("time").monotonic() - start >= 0.08

    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self, monkeypatch):
        from maru_deep_pro_search.engines.base import SearchEngine, NetworkError
        engine = SearchEngineRegistry.create("duckduckgo")
        monkeypatch.setattr(
            engine._circuit_breaker,
            "can_execute",
            lambda: (_ for _ in ()).throw(NetworkError("open", retryable=False)),
        )
        with pytest.raises(NetworkError):
            await engine.search("test", max_results=1)

    def test_text_helper_none(self):
        from maru_deep_pro_search.engines.base import _text
        assert _text(None) == ""

    def test_text_helper_get_all_text(self):
        from unittest.mock import MagicMock
        from maru_deep_pro_search.engines.base import _text
        el = MagicMock()
        el.text = None
        el.get_all_text.return_value = "  hello  "
        assert _text(el) == "hello"

    def test_guess_content_type_korean_github(self):
        from maru_deep_pro_search.engines.base import ContentType, _guess_content_type
        result = _guess_content_type("https://github.com/user/repo", "")
        assert result == ContentType.CODE

    def test_guess_source_type_value_error(self):
        from maru_deep_pro_search.engines.base import SourceType, guess_source_type_and_primary
        st, is_prim = guess_source_type_and_primary("https://unknown.com", "")
        assert st == SourceType.UNKNOWN

    def test_text_helper_with_text(self):
        from unittest.mock import MagicMock
        from maru_deep_pro_search.engines.base import _text
        el = MagicMock()
        el.text = "  hello world  "
        assert _text(el) == "hello world"

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_search(self, monkeypatch):
        from maru_deep_pro_search.engines.base import SearchEngine, NetworkError
        engine = SearchEngineRegistry.create("duckduckgo")

        async def _false():
            return False

        monkeypatch.setattr(engine._circuit_breaker, "can_execute", _false)
        with pytest.raises(NetworkError, match="circuit breaker is open"):
            await engine.search("test", max_results=1)

    def test_guess_source_type_invalid_enum(self, monkeypatch):
        from maru_deep_pro_search.engines.base import SourceType, guess_source_type_and_primary
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.url.classify_source_type",
            lambda url, snippet="": "invalid_type",
        )
        st, _ = guess_source_type_and_primary("https://example.com", "")
        assert st == SourceType.UNKNOWN
