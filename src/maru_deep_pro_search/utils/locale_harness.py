"""Locale-aware query optimization harness for region-specific search engines.

When a user queries in English but targets a Chinese or Korean engine,
the harness appends localized keywords to improve result relevance.
It also detects when the query is already in the target language and
skips transformation in that case.
"""

from __future__ import annotations

import re

# Common tech-term mappings: English → localized equivalents
_TECH_TERMS = {
    "baidu": {
        "tutorial": "教程",
        "guide": "指南",
        "documentation": "文档",
        "example": "示例",
        "best practice": "最佳实践",
        "intro": "简介",
        "overview": "概述",
    },
    "naver": {
        "tutorial": "튜토리얼",
        "guide": "가이드",
        "documentation": "문서",
        "example": "예제",
        "best practice": "베스트 프랙티스",
        "intro": "소개",
        "overview": "개요",
    },
}

# Locale-specific suffixes to append to English queries
_LOCALE_SUFFIXES = {
    "baidu": ["教程", "详解", "文档"],
    "naver": ["강의", "튜토리얼", "설명"],
}

# Scripts that indicate a query is already localized
_LOCALE_SCRIPTS = {
    "baidu": re.compile(r"[\u4e00-\u9fff]"),  # CJK Unified Ideographs
    "naver": re.compile(r"[\uac00-\ud7af]"),  # Hangul Syllables
}


def _has_script(text: str, engine: str) -> bool:
    """Check if text already contains target-locale characters."""
    pattern = _LOCALE_SCRIPTS.get(engine)
    if not pattern:
        return False
    return bool(pattern.search(text))


def _replace_tech_terms(query: str, engine: str) -> str:
    """Replace known English tech terms with localized equivalents."""
    terms = _TECH_TERMS.get(engine, {})
    result = query
    for en, localized in terms.items():
        # Word-boundary replacement (case-insensitive)
        pattern = re.compile(rf"\b{re.escape(en)}\b", re.IGNORECASE)
        result = pattern.sub(localized, result)
    return result


def optimize_for_engine(query: str, engine_name: str) -> str:
    """Optimize a query for a region-specific search engine.

    Args:
        query: Original search query (any language).
        engine_name: Target engine name (e.g., "baidu", "naver").

    Returns:
        Optimized query string. If the query is already in the target
        language, it is returned unchanged.
    """
    engine = engine_name.lower()

    # Only Baidu and Naver currently benefit from localization
    if engine not in ("baidu", "naver"):
        return query

    # Skip if query already contains target-locale characters
    if _has_script(query, engine):
        return query

    # Replace known tech terms
    optimized = _replace_tech_terms(query, engine)

    # If no terms were replaced, append a locale-specific suffix
    if optimized == query:
        suffixes = _LOCALE_SUFFIXES.get(engine, [])
        if suffixes:
            # Use the first suffix as a sensible default
            optimized = f"{query} {suffixes[0]}"

    return optimized


def get_locale_hint(engine_name: str) -> str:
    """Return a human-readable hint about the engine's preferred language."""
    hints = {
        "baidu": "中文 (Chinese)",
        "naver": "한국어 (Korean)",
        "yahoo": "English",
        "google": "English",
        "bing": "English",
        "duckduckgo": "English",
        "duckduckgo_lite": "English",
        "startpage": "English",
        "ecosia": "English",
        "brave": "English",
    }
    return hints.get(engine_name.lower(), "English")
