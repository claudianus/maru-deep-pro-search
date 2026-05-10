"""Search engine registry — factory and discovery for multi-engine support."""

from __future__ import annotations

import logging
from typing import Type

from .base import SearchEngine

logger = logging.getLogger(__name__)


class SearchEngineRegistry:
    """Registry for search engine implementations."""

    _engines: dict[str, Type[SearchEngine]] = {}

    @classmethod
    def register(cls, name: str, engine_class: Type[SearchEngine]) -> None:
        """Register a search engine class."""
        cls._engines[name] = engine_class
        logger.debug("Registered search engine: %s", name)

    @classmethod
    def get(cls, name: str) -> Type[SearchEngine]:
        """Get engine class by name."""
        if name not in cls._engines:
            available = ", ".join(cls._engines.keys())
            raise ValueError(
                f"Unknown engine '{name}'. Available: {available}"
            )
        return cls._engines[name]

    @classmethod
    def create(cls, name: str, **kwargs) -> SearchEngine:
        """Create an engine instance by name."""
        engine_class = cls.get(name)
        return engine_class(**kwargs)

    @classmethod
    def list_engines(cls) -> list[str]:
        """List all registered engine names."""
        return list(cls._engines.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an engine is registered."""
        return name in cls._engines


# Auto-register built-in engines
def _register_builtins() -> None:
    try:
        from .duckduckgo import DuckDuckGoEngine
        SearchEngineRegistry.register("duckduckgo", DuckDuckGoEngine)
        SearchEngineRegistry.register("duckduckgo_lite", DuckDuckGoEngine)
    except ImportError as exc:
        logger.warning("Could not register DuckDuckGo engine: %s", exc)

    try:
        from .searxng import SearXNGEngine
        SearchEngineRegistry.register("searxng", SearXNGEngine)
    except ImportError as exc:
        logger.warning("Could not register SearXNG engine: %s", exc)

    try:
        from .bing import BingEngine
        SearchEngineRegistry.register("bing", BingEngine)
    except ImportError as exc:
        logger.warning("Could not register Bing engine: %s", exc)

    try:
        from .naver import NaverEngine
        SearchEngineRegistry.register("naver", NaverEngine)
    except ImportError as exc:
        logger.warning("Could not register Naver engine: %s", exc)

    try:
        from .qwant import QwantEngine
        SearchEngineRegistry.register("qwant", QwantEngine)
    except ImportError as exc:
        logger.warning("Could not register Qwant engine: %s", exc)

    try:
        from .google import GoogleEngine
        SearchEngineRegistry.register("google", GoogleEngine)
    except ImportError as exc:
        logger.warning("Could not register Google engine: %s", exc)


_register_builtins()
