"""Search engine registry — factory and discovery for multi-engine support."""

from __future__ import annotations

import logging

from .base import SearchEngine

logger = logging.getLogger(__name__)

# Fetch-only aliases — must not appear in SERP recommend_engines().
_FETCH_ONLY_ENGINES = frozenset({"duckduckgo_fetch"})


class SearchEngineRegistry:
    """Registry for search engine implementations."""

    _engines: dict[str, type[SearchEngine]] = {}
    _instances: dict[str, SearchEngine] = {}

    @classmethod
    def register(cls, name: str, engine_class: type[SearchEngine]) -> None:
        """Register a search engine class."""
        cls._engines[name] = engine_class
        logger.debug("Registered search engine: %s", name)

    @classmethod
    def get(cls, name: str) -> type[SearchEngine]:
        """Get engine class by name."""
        if name not in cls._engines:
            available = ", ".join(cls._engines.keys())
            raise ValueError(f"Unknown engine '{name}'. Available: {available}")
        return cls._engines[name]

    @classmethod
    def create(cls, name: str, **kwargs) -> SearchEngine:
        """Create or retrieve a cached engine instance by name.

        Instances are cached to reuse expensive resources (e.g. browser sessions).
        """
        if name not in cls._instances:
            engine_class = cls.get(name)
            cls._instances[name] = engine_class(**kwargs)
        return cls._instances[name]

    @classmethod
    def list_engines(cls) -> list[str]:
        """List all registered engine names."""
        return list(cls._engines.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an engine is registered."""
        return name in cls._engines

    @classmethod
    def recommend_engines(cls, query: str = "", count: int = 3) -> list[str]:
        """Recommend optimal engine combination based on metadata and query locale.

        TIER 1 engines are always preferred. Locale-aware boosts ensure Korean
        queries hit Naver, Chinese queries hit Baidu, and English queries stay
        on Western engines for best results.

        Args:
            query: Optional query hint for locale-aware engine selection.
            count: Number of engines to recommend (default: 3).

        Returns:
            List of engine names sorted by quality tier and reliability.
        """
        engines = cls.list_engines()
        scored: list[tuple[str, int, float, float]] = []

        # Locale detection for query-aware boosting
        locale_boosts: dict[str, float] = {}
        if query:
            import re

            if re.search(r"[\uac00-\ud7af]", query):  # Hangul
                locale_boosts["naver"] = 2.0
            if re.search(r"[\u4e00-\u9fff]", query):  # CJK
                locale_boosts["baidu"] = 2.0

            from ..research.fetch_planner import detect_query_intent

            intent = detect_query_intent(query)
            if intent == "security":
                locale_boosts["bing"] = locale_boosts.get("bing", 0.0) + 1.5
            elif intent == "docs":
                locale_boosts["bing"] = locale_boosts.get("bing", 0.0) + 1.0
                locale_boosts["startpage"] = locale_boosts.get("startpage", 0.0) + 0.5

        for name in engines:
            if name in _FETCH_ONLY_ENGINES:
                continue
            try:
                eng_cls = cls.get(name)
                reliability = eng_cls.reliability_score + locale_boosts.get(name, 0.0)
                scored.append(
                    (name, eng_cls.quality_tier, reliability, locale_boosts.get(name, 0.0))
                )
            except Exception:
                continue

        # Sort by tier ascending (1 is best), then reliability descending,
        # then locale boost descending (prefer locale-matched engines)
        scored.sort(key=lambda x: (x[1], -x[2], -x[3]))
        return [name for name, _, _, _ in scored[:count]]


# Auto-register built-in engines
def _register_builtins() -> None:
    engines_to_register = [
        ("duckduckgo", ".duckduckgo", "DuckDuckGoEngine"),
        ("duckduckgo_lite", ".duckduckgo", "DuckDuckGoEngine"),
        ("bing", ".bing", "BingEngine"),
        ("naver", ".naver", "NaverEngine"),
        ("google", ".google", "GoogleEngine"),
        ("startpage", ".startpage", "StartpageEngine"),
        ("yahoo", ".yahoo", "YahooEngine"),
        ("ecosia", ".ecosia", "EcosiaEngine"),
        ("baidu", ".baidu", "BaiduEngine"),
    ]

    for name, module_path, class_name in engines_to_register:
        try:
            module = __import__(
                f"maru_deep_pro_search.engines{module_path}",
                fromlist=[class_name],
            )
            engine_class = getattr(module, class_name)
            SearchEngineRegistry.register(name, engine_class)
        except ImportError as exc:
            logger.warning("Could not register %s engine: %s", name, exc)

    # Separate instance/CB for page fetch vs SERP search (same implementation class).
    if SearchEngineRegistry.is_registered("duckduckgo_lite"):
        SearchEngineRegistry.register(
            "duckduckgo_fetch",
            SearchEngineRegistry.get("duckduckgo_lite"),
        )


_register_builtins()
