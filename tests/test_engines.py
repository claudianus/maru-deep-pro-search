"""Tests for search engine registry and multi-engine support."""

import pytest

from maru_search.engines.registry import SearchEngineRegistry
from maru_search.engines.base import SearchEngine


class TestSearchEngineRegistry:
    def test_all_engines_registered(self):
        engines = SearchEngineRegistry.list_engines()
        assert "duckduckgo" in engines
        assert "duckduckgo_lite" in engines
        assert "searxng" in engines
        assert "bing" in engines
        assert "naver" in engines
        assert "qwant" in engines
        assert len(engines) >= 6

    def test_create_duckduckgo(self):
        engine = SearchEngineRegistry.create("duckduckgo")
        assert engine.name == "duckduckgo"

    def test_create_duckduckgo_lite(self):
        engine = SearchEngineRegistry.create("duckduckgo_lite")
        assert engine.name == "duckduckgo"

    def test_create_searxng(self):
        engine = SearchEngineRegistry.create("searxng")
        assert engine.name == "searxng"
        assert hasattr(engine, "instances")

    def test_create_bing(self):
        engine = SearchEngineRegistry.create("bing")
        assert engine.name == "bing"

    def test_create_naver(self):
        engine = SearchEngineRegistry.create("naver")
        assert engine.name == "naver"

    def test_create_qwant(self):
        engine = SearchEngineRegistry.create("qwant")
        assert engine.name == "qwant"

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            SearchEngineRegistry.create("nonexistent")

    def test_create_google(self):
        engine = SearchEngineRegistry.create("google")
        assert engine.name == "google"

    def test_is_registered(self):
        assert SearchEngineRegistry.is_registered("searxng")
        assert SearchEngineRegistry.is_registered("bing")
        assert SearchEngineRegistry.is_registered("google")
        assert not SearchEngineRegistry.is_registered("yahoo")
