"""Query expansion for deep research.

Generates orthogonal subqueries to cover multiple angles of a research topic
without requiring LLM calls."""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Template-based query expansion angles
_QUERY_TEMPLATES = {
    "recent": [
        "{query} latest 2025 2026",
        "{query} new features updates",
        "{query} recent developments",
    ],
    "tutorial": [
        "{query} tutorial getting started",
        "{query} beginner guide examples",
        "{query} how to use",
    ],
    "api": [
        "{query} API reference documentation",
        "{query} function methods parameters",
        "{query} SDK docs",
    ],
    "troubleshooting": [
        "{query} common errors solutions",
        "{query} fix problem troubleshooting",
        "{query} error handling",
    ],
    "comparison": [
        "{query} vs alternative comparison",
        "{query} best practices",
        "{query} benchmark performance",
    ],
    "github": [
        "{query} github repository examples",
        "{query} open source implementation",
        "{query} code samples",
    ],
    "community": [
        "{query} stackoverflow discussion",
        "{query} reddit community",
        "{query} forum discussion",
    ],
}


def expand_query(query: str, max_subqueries: int = 5) -> list[str]:
    """Expand a query into multiple orthogonal subqueries.

    Args:
        query: Original search query.
        max_subqueries: Maximum number of subqueries to generate.

    Returns:
        List of subqueries including the original.
    """
    subqueries = [query]  # Always include original

    # Select angles based on query characteristics
    angles = _select_angles(query)

    for angle in angles:
        templates = _QUERY_TEMPLATES.get(angle, [])
        for template in templates:
            subquery = template.format(query=query)
            if subquery not in subqueries:
                subqueries.append(subquery)
            if len(subqueries) >= max_subqueries:
                break
        if len(subqueries) >= max_subqueries:
            break

    logger.debug("Expanded query '%s' into %d subqueries", query, len(subqueries))
    return subqueries[:max_subqueries]


def _select_angles(query: str) -> list[str]:
    """Select relevant expansion angles based on query content."""
    lower = query.lower()
    angles = []

    # Always include recent
    angles.append("recent")

    # Code-related queries
    if any(kw in lower for kw in ["python", "javascript", "typescript", "go", "rust", "java", "code", "programming", "api", "library", "framework"]):
        angles.extend(["tutorial", "api", "github"])

    # Error/problem queries
    if any(kw in lower for kw in ["error", "fix", "problem", "issue", "bug", "troubleshoot"]):
        angles.extend(["troubleshooting", "community"])

    # Comparison queries
    if any(kw in lower for kw in ["vs", "versus", "compare", "alternative", "best"]):
        angles.append("comparison")

    # General tech queries
    if not angles:
        angles.extend(["tutorial", "comparison"])

    return angles


def extract_keywords(query: str) -> list[str]:
    """Extract key terms from a query for relevance scoring."""
    # Remove common stop words
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "can", "need", "dare", "ought", "used", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into",
        "through", "during", "before", "after", "above", "below",
        "between", "under", "again", "further", "then", "once",
        "here", "there", "when", "where", "why", "how", "all",
        "each", "few", "more", "most", "other", "some", "such",
        "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "just", "and", "but", "if", "or", "because",
        "until", "while", "what", "which", "who", "whom", "this",
        "that", "these", "those", "am", "it", "its", "about",
        "against", "down", "out", "off", "over", "under", "again",
        "further", "then", "once", "i", "me", "my", "myself", "we",
        "our", "ours", "ourselves", "you", "your", "yours", "yourself",
        "yourselves", "he", "him", "his", "himself", "she", "her",
        "hers", "herself", "they", "them", "their", "theirs",
        "themselves", "get", "using", "use", "how", "tutorial",
        "guide", "example", "sample", "documentation", "docs",
    }

    words = re.findall(r'\b[a-zA-Z]+\b', query.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    return keywords
