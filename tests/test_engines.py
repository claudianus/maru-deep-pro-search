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
