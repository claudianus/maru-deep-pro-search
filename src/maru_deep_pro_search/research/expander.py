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
        "{domain} {_CURRENT_YEAR} developer survey popularity",
    ],
    "trends_benchmark": [
        "{domain} benchmark comparison {_CURRENT_YEAR}",
        "{domain} performance test {_CURRENT_YEAR}",
    ],
    "trends_official": [
        "{domain} official documentation latest",
        "{domain} {_CURRENT_YEAR} new features changelog",
    ],
    "trends_authority": [
        "{domain} {_CURRENT_YEAR} architecture best practices",
    ],
    "trends_community": [
        "{domain} Reddit discussion experiences {_CURRENT_YEAR}",
        "{domain} Hacker News thread {_CURRENT_YEAR}",
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

    Strips action words, years, and filler to get concise subject
    matter (e.g., "how to install Next.js" → "Next.js",
    "Full-stack web development trends 2026" → "full stack",
    "React 19 new features" → "react").
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

    # Remove years (2020–2029) to prevent duplication with template {_CURRENT_YEAR}
    domain = re.sub(r"\b20\d{2}\b", "", domain)

    # Remove trailing context words (features, practices, patterns, etc.)
    domain = re.sub(
        r"\s+(new features|features|best practices|practices|patterns|"
        r"tutorial|guide|example|vs|versus|comparison|performance|"
        r"speed|latency|throughput|memory|error|fix|solution).*$",
        "", domain,
    )

    # Normalize hyphens to spaces before removing filler words
    # so "full-stack" becomes "full stack" and removing "stack" leaves "full"
    domain = domain.replace("-", " ")

    # Remove common filler words that bloat queries
    # NOTE: "stack" is intentionally kept (e.g., "full stack", "MEAN stack")
    fillers = [
        r"\bweb\b", r"\bdevelopment\b", r"\bdeveloper\b", r"\btechnology\b",
        r"\btechnologies\b", r"\bframework\b", r"\bframeworks\b", r"\btool\b",
        r"\btools\b", r"\becosystem\b", r"\blandscape\b",
        r"\bmost\b", r"\bpopular\b", r"\bused\b", r"\badoption\b",
    ]
    for f in fillers:
        domain = re.sub(f, "", domain, flags=re.IGNORECASE)

    # Collapse multiple spaces
    domain = re.sub(r"\s+", " ", domain).strip()

    # Limit length — search engines handle short queries better
    if len(domain) > 40:
        words = domain.split()
        domain = " ".join(words[:4])

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
