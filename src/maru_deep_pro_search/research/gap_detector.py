"""Gap detection for iterative deep research.

Analyzes crawled sources against the original query to identify
uncovered topics and suggest follow-up search queries.
"""

from __future__ import annotations

from .expander import extract_keywords

# Research angles that are commonly valuable
_RESEARCH_ANGLES = [
    "benchmark performance",
    "security vulnerability",
    "production deployment",
    "migration guide",
    "best practices",
    "common errors",
    "official documentation",
    "github repository",
    "release notes",
]


def detect_gaps(query: str, sources: list) -> list[str]:
    """Analyze sources and suggest follow-up queries.

    Args:
        query: Original search query.
        sources: List of CitedSource objects.

    Returns:
        List of suggested follow-up queries (max 3).
    """
    if not sources:
        return []

    # Extract query keywords
    query_keywords = set(extract_keywords(query))
    if not query_keywords:
        return []

    # Collect all text from sources
    source_text = ""
    for src in sources:
        if hasattr(src, "markdown") and src.markdown:
            source_text += src.markdown + " "
        if hasattr(src, "content") and src.content:
            source_text += src.content + " "
        if hasattr(src, "snippet") and src.snippet:
            source_text += src.snippet + " "
    source_text = source_text.lower()

    # Check which query keywords are poorly covered
    uncovered_keywords = [kw for kw in query_keywords if kw not in source_text and len(kw) > 3]

    # Check which research angles are uncovered
    uncovered_angles: list[str] = []
    for angle in _RESEARCH_ANGLES:
        if angle not in source_text:
            uncovered_angles.append(angle)

    # Build suggestions
    suggestions: list[str] = []

    # Priority 1: uncovered keywords + angle
    for kw in uncovered_keywords[:2]:
        for angle in uncovered_angles[:2]:
            suggestions.append(f"{kw} {angle}")
            if len(suggestions) >= 3:
                break
        if len(suggestions) >= 3:
            break

    # Priority 2: original query + uncovered angle
    if len(suggestions) < 3:
        for angle in uncovered_angles:
            if angle.lower() not in query.lower():
                suggestions.append(f"{query} {angle}")
                if len(suggestions) >= 3:
                    break

    # Priority 3: original query + benchmark/security if nothing else
    if not suggestions:
        if "benchmark" not in query.lower():
            suggestions.append(f"{query} benchmark")
        if "security" not in query.lower() and len(suggestions) < 3:
            suggestions.append(f"{query} security")

    return suggestions[:3]
