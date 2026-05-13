"""Query expansion for deep research — intent-aware orthogonal angles.

Generates semantically diverse subqueries to cover multiple research angles
without requiring LLM calls. Each angle targets a different information type
(survey data, benchmarks, official docs, community consensus, etc.).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

_CURRENT_YEAR = datetime.now().year

# ---------------------------------------------------------------------------
# Intent-aware query expansion templates
# Each intent has ORTHOGONAL angles — no two angles produce similar results.
# ---------------------------------------------------------------------------

_QUERY_TEMPLATES = {
    # ── Trends / Landscape (default for broad tech queries) ──
    "trends_survey": [
        "State of {domain} {_CURRENT_YEAR} survey results developer",
        "Stack Overflow developer survey {_CURRENT_YEAR} {domain} most popular",
        "GitHub Octoverse {_CURRENT_YEAR} {domain} trends",
    ],
    "trends_benchmark": [
        "{domain} benchmark comparison {_CURRENT_YEAR} performance",
        "{domain} vs alternative speed latency throughput {_CURRENT_YEAR}",
    ],
    "trends_official": [
        "{domain} official documentation latest updates release notes",
        "{domain} {_CURRENT_YEAR} new features changelog",
    ],
    "trends_authority": [
        "ThoughtWorks technology radar {_CURRENT_YEAR} {domain}",
        "Gartner Hype Cycle {_CURRENT_YEAR} {domain}",
        "Martin Fowler {domain} architecture {_CURRENT_YEAR}",
    ],
    "trends_community": [
        "{domain} Reddit discussion experiences pros cons {_CURRENT_YEAR}",
        "Hacker News {domain} thread {_CURRENT_YEAR}",
        "{domain} dev.to community insights",
    ],

    # ── How-To / Tutorial ──
    "howto_install": [
        "{domain} install setup getting started {_CURRENT_YEAR}",
        "{domain} official quickstart guide",
    ],
    "howto_examples": [
        "{domain} code examples tutorial real world",
        "{domain} github repository sample project",
    ],
    "howto_pitfalls": [
        "{domain} common mistakes anti patterns avoid",
        "{domain} best practices do and don't",
    ],

    # ── Comparison ──
    "compare_alternative": [
        "{domain} vs best alternative {_CURRENT_YEAR} comparison",
        "{domain} versus when to choose which",
    ],
    "compare_benchmark": [
        "{domain} benchmark performance latency memory {_CURRENT_YEAR}",
        "{domain} load test scalability comparison",
    ],
    "compare_ecosystem": [
        "{domain} ecosystem plugins libraries {_CURRENT_YEAR}",
        "{domain} community size adoption rate",
    ],

    # ── Debug / Problem-Solving ──
    "debug_errors": [
        "{domain} common error fix solution",
        "{domain} troubleshooting stackoverflow",
    ],
    "debug_issues": [
        "{domain} github issues open bugs {_CURRENT_YEAR}",
        "{domain} deprecated removed migration guide",
    ],

    # ── Definition / Concept ──
    "def_official": [
        "{domain} official documentation what is overview",
        "{domain} wikipedia definition architecture",
    ],
    "def_simple": [
        "{domain} explained simply beginner introduction",
        "{domain} core concepts how it works",
    ],

    # ── News / Recent ──
    "news_latest": [
        "{domain} latest news {_CURRENT_YEAR} release",
        "{domain} announcement blog post {_CURRENT_YEAR}",
    ],
    "news_release": [
        "{domain} release notes changelog {_CURRENT_YEAR}",
        "{domain} version latest stable",
    ],
}

# Mapping: intent → ordered list of angles (priority order)
_INTENT_ANGLES = {
    "trends": [
        "trends_survey", "trends_benchmark", "trends_official",
        "trends_authority", "trends_community",
    ],
    "howto": [
        "howto_install", "howto_examples", "howto_pitfalls",
    ],
    "comparison": [
        "compare_alternative", "compare_benchmark", "compare_ecosystem",
    ],
    "debug": [
        "debug_errors", "debug_issues",
    ],
    "definition": [
        "def_official", "def_simple",
    ],
    "news": [
        "news_latest", "news_release", "trends_official",
    ],
    "korean": [
        "korean_community", "korean_docs", "recent_general",
    ],
}

# Stable concepts — skip "latest YYYY" noise for these
_STABLE_CONCEPTS = {
    "list comprehension", "dictionary", "tuple", "set", "string",
    "for loop", "while loop", "if statement", "function", "class",
    "inheritance", "polymorphism", "encapsulation", "recursion",
    "ownership", "borrowing", "lifetime", "trait", "struct", "enum",
    "closure", "iterator", "generics", "macro",
    "variable", "constant", "scope", "namespace", "module",
    "http", "tcp", "udp", "rest", "json", "xml", "yaml",
    "algorithm", "data structure", "big o", "complexity",
    "sort", "search", "tree", "graph", "queue", "stack", "heap",
}


def expand_query(query: str, max_subqueries: int = 8) -> list[str]:
    """Expand a query into multiple orthogonal subqueries.

    Args:
        query: Original search query.
        max_subqueries: Maximum number of subqueries to generate.
            Increased from 5 → 8 to improve coverage.

    Returns:
        List of subqueries including the original.
    """
    subqueries = [query]

    intent = _detect_intent(query)
    angles = _INTENT_ANGLES.get(intent, _INTENT_ANGLES["trends"])

    # Extract domain terms for template substitution
    domain = _extract_domain(query)

    for angle in angles:
        templates = _QUERY_TEMPLATES.get(angle, [])
        for template in templates:
            subquery = template.format(
                query=query,
                domain=domain,
                _CURRENT_YEAR=_CURRENT_YEAR,
            )
            if subquery not in subqueries:
                subqueries.append(subquery)
            if len(subqueries) >= max_subqueries:
                break
        if len(subqueries) >= max_subqueries:
            break

    logger.debug(
        "Expanded query '%s' (intent=%s) into %d subqueries",
        query[:60], intent, len(subqueries),
    )
    return subqueries[:max_subqueries]


def _detect_intent(query: str) -> str:
    """Detect query intent for angle selection."""
    lower = query.lower()

    # Korean language queries → preserve original Korean expansion behavior
    has_korean = any('\uac00' <= char <= '\ud7a3' for char in query)
    korean_keywords = ["한국", "국내", "korean", "한글", "한국어"]
    if has_korean or any(kw in lower for kw in korean_keywords):
        return "korean"

    # Comparison intent
    if any(k in lower for k in [
        " vs ", " versus ", "compare", "comparison",
        "difference between", "diff between", "which is better",
        "pros and cons", "advantages disadvantages",
    ]):
        return "comparison"

    # How-To intent
    if any(k in lower for k in [
        "how to ", "install ", "setup ", "configure ", "deploy ",
        "getting started", "tutorial", "guide", "learn ", "beginner",
        "quickstart", "step by step",
    ]):
        return "howto"

    # Debug / Problem intent
    if any(k in lower for k in [
        "error", "fix", "deprecated", "removed", "alternative",
        "migrate", "troubleshoot", "issue", "problem", "bug",
        "solution", "workaround", "broken", "fail",
    ]):
        return "debug"

    # Definition intent
    if any(k in lower for k in [
        "what is ", "meaning of", "define ", "definition",
        "explain ", "introduction to ", "overview of",
    ]):
        return "definition"

    # News / Recent intent (strong signal)
    if any(k in lower for k in [
        "latest", "news", "update", "release", "announcement",
        "just released", "new version", "changelog",
    ]):
        return "news"

    # Trends / Landscape (default for broad queries)
    if any(k in lower for k in [
        "trends", "trend", "stack", "ecosystem", "landscape",
        "technology", "frameworks", "tools", "popular",
        "most used", "adoption", "state of",
    ]):
        return "trends"

    # Default to trends for broad technical queries
    return "trends"


def _extract_domain(query: str) -> str:
    """Extract the core domain/technology terms from query.

    Used for template substitution. Strips action words to get
    the subject matter (e.g., "how to install Next.js" → "Next.js").
    """
    lower = query.lower()

    # Remove common action prefixes
    prefixes = [
        r"^how to\s+",
        r"^what is\s+",
        r"^install\s+",
        r"^setup\s+",
        r"^configure\s+",
        r"^deploy\s+",
        r"^compare\s+",
        r"^difference between\s+",
        r"^vs\s+",
        r"^best\s+",
        r"^latest\s+",
        r"^new\s+",
        r"^top\s+",
        r"^trends?\s+(in\s+)?",
    ]
    domain = lower
    for p in prefixes:
        domain = re.sub(p, "", domain, flags=re.IGNORECASE)

    # Remove trailing noise
    domain = re.sub(r"\s+(tutorial|guide|example|vs|versus|comparison).*$", "", domain)
    domain = domain.strip()

    # Capitalize first letter for better search results
    if domain:
        domain = domain[0].upper() + domain[1:]

    return domain or query


def extract_keywords(query: str) -> list[str]:
    """Extract key terms from a query for relevance scoring."""
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
        "against", "down", "out", "off", "over", "i", "me", "my", "myself", "we",
        "our", "ours", "ourselves", "you", "your", "yours", "yourself",
        "yourselves", "he", "him", "his", "himself", "she", "her",
        "hers", "herself", "they", "them", "their", "theirs",
        "themselves", "get", "using", "use", "tutorial",
        "guide", "example", "sample", "documentation", "docs",
    }

    words = re.findall(r'\b[a-zA-Z]+\b', query.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    return keywords
