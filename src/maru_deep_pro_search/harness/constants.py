"""Shared harness constants for research gate and drift detection."""

from __future__ import annotations

RESEARCH_PRODUCING_TOOLS: frozenset[str] = frozenset(
    {
        "deep_research",
        "answer",
        "web_search",
        "search_with_citations",
        "parallel_search",
        "fetch_page",
        "fetch_bulk",
        "stealthy_fetch",
    }
)

RESEARCH_AUGMENTING_TOOLS: frozenset[str] = frozenset(
    {"fetch_page", "fetch_bulk", "stealthy_fetch"}
)

FRESH_RESEARCH_REQUIRED_TOOLS: frozenset[str] = frozenset({"generate_code", "export_research"})

BYPASS_SEARCH_TOOLS: frozenset[str] = frozenset(
    {
        "WebSearch",
        "WebFetch",
        "BrowserAction",
        "search_web",
        "google_search",
        "brave_search",
    }
)

RESEARCH_EXEMPT_META_TOOLS: frozenset[str] = frozenset(
    {
        "version",
        "list_engines",
        "engine_health",
        "session_state",
        "drift_status",
        "query_knowledge",
        "cache_stats",
        "clear_caches",
    }
)

# Lockfiles alone should not force re-research warnings.
SOFT_DRIFT_FILES: frozenset[str] = frozenset(
    {
        "uv.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "Cargo.lock",
        "go.sum",
        "poetry.lock",
        "Pipfile.lock",
    }
)

HARD_DRIFT_FILES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        "requirements-dev.txt",
        "Cargo.toml",
        "go.mod",
        "Pipfile",
    }
)
