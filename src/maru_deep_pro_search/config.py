"""Configuration management for maru-search.

Supports environment variables and sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SearchConfig:
    """Runtime search configuration."""

    default_engine: str = "duckduckgo_lite"
    max_results_per_query: int = 10
    deep_max_sources: int = 30
    deep_max_subqueries: int = 7
    serp_per_engine_cap: int = 50
    answer_balanced_max_sources: int = 14
    answer_deep_max_sources: int = 30
    answer_deep_fetch_count: int = 6
    max_concurrent_fetches: int = 5
    knowledge_reuse_max_chars: int = 4000
    research_context_max_chars: int = 8000
    wrapper_tier: str = "tiered"  # tiered | full
    # --- HTTP timeouts (seconds) — read by MCP tools -----------------------------
    serp_timeout_seconds: float = 30.0
    """Timeout for search-engine HTML scrape (``web_search``, ``search_with_citations``)."""

    http_fetch_timeout_seconds: float = 20.0
    """Timeout for ``fetch_page`` / each URL in ``fetch_bulk``."""

    deep_research_timeout_seconds: float = 60.0
    """Timeout for ``deep_research(...)`` orchestration."""

    deep_serp_run_timeout_seconds: float = 10.0
    """Timeout for each subquery/engine run inside ``deep_research``."""

    answer_timeout_seconds: float = 60.0
    """Timeout for ``tool_answer`` (deep pipeline)."""

    auto_fetch_nested_timeout_seconds: float = 8.0
    """Budget for each nested ``fetch_page`` during ``deep_research`` ``auto_fetch``."""

    retry_attempts: int = 3
    # Auto-update settings
    auto_check_updates: bool = True
    # Quality weights for ranking
    authority_weight: float = 2.0
    freshness_weight: float = 1.0
    snippet_weight: float = 1.0
    position_weight: float = 0.5

    @classmethod
    def from_env(cls) -> SearchConfig:
        """Load configuration from environment variables."""
        wrapper = os.getenv("MARU_WRAPPER_TIER", "tiered").strip().lower()
        if wrapper not in ("tiered", "full"):
            wrapper = "tiered"
        return cls(
            default_engine=os.getenv("MARU_SEARCH_ENGINE", "duckduckgo_lite"),
            max_results_per_query=int(os.getenv("MARU_SEARCH_MAX_RESULTS", "10")),
            deep_max_sources=int(os.getenv("MARU_DEEP_MAX_SOURCES", "30")),
            deep_max_subqueries=int(os.getenv("MARU_DEEP_MAX_SUBQUERIES", "7")),
            serp_per_engine_cap=int(os.getenv("MARU_SERP_PER_ENGINE_CAP", "50")),
            answer_balanced_max_sources=int(os.getenv("MARU_ANSWER_BALANCED_MAX_SOURCES", "14")),
            answer_deep_max_sources=int(os.getenv("MARU_ANSWER_DEEP_MAX_SOURCES", "30")),
            answer_deep_fetch_count=int(os.getenv("MARU_ANSWER_DEEP_FETCH_COUNT", "6")),
            max_concurrent_fetches=int(os.getenv("MARU_SEARCH_MAX_CONCURRENT", "5")),
            knowledge_reuse_max_chars=int(os.getenv("MARU_KNOWLEDGE_REUSE_MAX_CHARS", "4000")),
            research_context_max_chars=int(os.getenv("MARU_RESEARCH_CONTEXT_MAX_CHARS", "8000")),
            wrapper_tier=wrapper,
            authority_weight=float(os.getenv("MARU_AUTHORITY_WEIGHT", "2.0")),
            freshness_weight=float(os.getenv("MARU_FRESHNESS_WEIGHT", "1.0")),
            snippet_weight=float(os.getenv("MARU_SNIPPET_WEIGHT", "1.0")),
            position_weight=float(os.getenv("MARU_POSITION_WEIGHT", "0.5")),
            serp_timeout_seconds=float(os.getenv("MARU_SEARCH_TIMEOUT", "30.0")),
            http_fetch_timeout_seconds=float(os.getenv("MARU_FETCH_HTTP_TIMEOUT", "20.0")),
            deep_research_timeout_seconds=float(os.getenv("MARU_DEEP_RESEARCH_TIMEOUT", "60.0")),
            deep_serp_run_timeout_seconds=float(os.getenv("MARU_DEEP_SERP_RUN_TIMEOUT", "10.0")),
            answer_timeout_seconds=float(os.getenv("MARU_ANSWER_TIMEOUT", "60.0")),
            auto_fetch_nested_timeout_seconds=float(os.getenv("MARU_AUTO_FETCH_TIMEOUT", "8.0")),
            retry_attempts=int(os.getenv("MARU_SEARCH_RETRIES", "3")),
            auto_check_updates=os.getenv("MARU_SKIP_UPDATE_CHECK", "").lower()
            not in ("1", "true", "yes"),
        )


# Global default instance
DEFAULT_CONFIG = SearchConfig.from_env()
