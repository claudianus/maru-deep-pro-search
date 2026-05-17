"""Search-query gate: reject conversational queries; optimize for SERP retrieval.

No LLM — rule-based only. Host agents must rewrite rejected queries using hints.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .query_sanitize import sanitize_query

_CURRENT_YEAR = __import__("datetime").datetime.now().year

# Conversational / meta phrases that waste SERP slots
_CONVERSATIONAL_PREFIX = re.compile(
    r"^(?:"
    r"can you|could you|would you|please|help me|i want to|i need to|"
    r"tell me(?: about)?|what is|what are|explain(?: to me)?|"
    r"give me|show me|find me|look up|search for|research(?: about)?"
    r")\s+",
    re.I,
)
_CONVERSATIONAL_SUFFIX = re.compile(
    r"\s+(?:for me|please|thanks|thank you|\.{2,})\s*$",
    re.I,
)
_KOREAN_SEARCH_FILLER = re.compile(
    r"(?:"
    r"딥리서치(?:해서)?|리서치(?:해서)?|검색(?:해서)?|찾아(?:서)?|조사(?:해서)?|"
    r"알려줘|알려주세요|찾아줘|찾아주세요|검색해줘|검색해주세요|"
    r"추천해줘|추천해주세요|정리해줘|정리해주세요|해줘|해주세요"
    r")"
)

_VAGUE_ONLY = re.compile(
    r"^(?:"
    r"help|fix|issue|problem|error|research|search|info|information|"
    r"latest|update|news|tutorial|guide|docs?"
    r")\.?$",
    re.I,
)

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "about",
        "me",
        "my",
        "your",
        "our",
        "their",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "and",
        "or",
        "but",
        "if",
        "then",
        "so",
        "just",
        "also",
        "very",
        "really",
        "some",
        "any",
        "all",
        "how",
        "what",
        "when",
        "where",
        "why",
        "which",
        "who",
    }
)

_TECH_HINT = re.compile(
    r"\b(?:"
    r"api|sdk|library|framework|python|javascript|typescript|rust|go|java|"
    r"react|vue|nextjs|fastapi|django|flask|docker|kubernetes|aws|gcp|"
    r"mcp|llm|npm|pip|uv|github|cve|http|sql|redis|postgres"
    r")\b",
    re.I,
)
_SECURITY_HINT = re.compile(r"\b(cve|vulnerability|exploit|security|ghsa|advisory)\b", re.I)
_COMPARE_HINT = re.compile(r"\b(vs\.?|versus|compare|comparison|better than)\b", re.I)
_FRESHNESS_HINT = re.compile(
    r"\b(latest|current|recent|today|price|prices|recommendation|buy|used|market)\b|"
    r"(최신|현재|요즘|오늘|시세|가격|추천|중고|구매|가성비)"
)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

_MAX_QUERY_LEN = 180
_MIN_CHARS = 8
_MIN_KEYWORDS = 2

_GENERIC_TERMS = frozenset(
    {
        "fix",
        "fixed",
        "issue",
        "issues",
        "problem",
        "problems",
        "error",
        "errors",
        "bug",
        "bugs",
        "help",
        "broken",
        "wrong",
        "fail",
        "failed",
        "failing",
        "this",
        "that",
        "it",
        "something",
        "anything",
        "unknown",
        "user",
        "request",
        "task",
        "question",
        "message",
        "intent",
        "topic",
    }
)


@dataclass
class QueryPrepResult:
    """Outcome of query gate + optimizer."""

    original: str
    query: str
    passed_gate: bool
    reject_reason: str = ""
    hints: list[str] = field(default_factory=list)
    transformations: list[str] = field(default_factory=list)


def strict_query_gate_enabled() -> bool:
    return os.environ.get("MARU_STRICT_QUERY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"[\s,;]+", query.strip()) if t]


def _has_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def _meaningful_tokens(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t.lower() not in _STOPWORDS and len(t) > 1]


def validate_query_quality(query: str) -> tuple[bool, str, list[str]]:
    """Return (ok, reason, rewrite_hints)."""
    hints: list[str] = []
    q = query.strip()
    if len(q) < _MIN_CHARS:
        return (
            False,
            "Query too short for search engines (min ~8 characters).",
            [
                "`{library} {topic} official documentation " + str(_CURRENT_YEAR) + "`",
                "`{exact error message} fix stackoverflow`",
            ],
        )

    tokens = _tokens(q)
    meaningful = _meaningful_tokens(tokens)

    if len(meaningful) < _MIN_KEYWORDS:
        return (
            False,
            "Query lacks specific keywords (need ≥2 concrete terms, not filler words).",
            [
                "Remove: please, can you, tell me about, I want to",
                "Include: product/library name + aspect (install, API, CVE, vs)",
                f"Example: `httpx async client timeout {_CURRENT_YEAR}`",
            ],
        )

    if not any(t.lower() not in _GENERIC_TERMS for t in meaningful):
        return (
            False,
            "Query has no specific subject (only generic words like fix/error/this).",
            [
                f"Example: `ImportError httpx module not found fix {_CURRENT_YEAR}`",
                "Include the library, API, or exact error text from the stack trace.",
            ],
        )

    if _VAGUE_ONLY.match(q):
        return (
            False,
            "Query is a generic single word — not searchable.",
            hints or ["`FastAPI middleware order official documentation`"],
        )

    lowered = q.lower()
    if lowered in ("deep research", "research this", "search web", "look it up"):
        return (
            False,
            "Meta-instruction is not a search query.",
            [
                "Extract the TECHNICAL subject from the user request first.",
                f"Example: user wants auth → `JWT vs session cookies FastAPI {_CURRENT_YEAR}`",
            ],
        )

    # Mostly stopwords
    if tokens and len(meaningful) / max(len(tokens), 1) < 0.35:
        return (
            False,
            "Query is mostly filler words.",
            [f"Use 3–10 keywords: `{{name}} {{feature}} docs CVE benchmark {_CURRENT_YEAR}`"],
        )

    if len(q) > 512:
        return (
            False,
            "Query too long — search engines prefer concise keyword queries.",
            [
                "Shorten to ≤12 keywords; move context to fetch_page after search.",
            ],
        )

    return True, "", hints


def optimize_query_for_engine(query: str) -> tuple[str, list[str]]:
    """Deterministic SERP-oriented rewrite. Returns (optimized, transformation_labels)."""
    transforms: list[str] = []
    q = query.strip()
    if not q:
        return q, transforms

    original_len = len(q)
    q = _CONVERSATIONAL_PREFIX.sub("", q)
    q = _CONVERSATIONAL_PREFIX.sub("", q)
    q = q.strip(" ?.,;")
    q = _CONVERSATIONAL_SUFFIX.sub("", q)
    q = q.strip(" ?.,;")
    if len(q) < original_len:
        transforms.append("stripped_conversational")

    korean_cleaned = _KOREAN_SEARCH_FILLER.sub(" ", q)
    korean_cleaned = re.sub(r"\s+", " ", korean_cleaned).strip(" ?.,;")
    if korean_cleaned and len(korean_cleaned) >= _MIN_CHARS and korean_cleaned != q:
        q = korean_cleaned
        transforms.append("stripped_korean_filler")

    q = sanitize_query(q)
    if q != query.strip():
        transforms.append("fresh_year")

    # how-to → keyword form (keep subject)
    if re.match(r"^how\s+(?:do\s+i|can\s+i|to)\s+", q, re.I):
        q = re.sub(r"^how\s+(?:do\s+i|can\s+i|to)\s+", "", q, flags=re.I)
        transforms.append("howto_keywords")

    lowered = q.lower()
    if _SECURITY_HINT.search(q) and "cve" not in lowered and "advisory" not in lowered:
        q = f"{q} security advisory CVE"
        transforms.append("security_terms")

    if _COMPARE_HINT.search(q) and "comparison" not in lowered and " vs " not in lowered:
        q = f"{q} comparison benchmark"
        transforms.append("compare_terms")

    if _TECH_HINT.search(q) and not _YEAR_RE.search(q):
        q = f"{q} {_CURRENT_YEAR}"
        transforms.append("added_year")

    if _FRESHNESS_HINT.search(q) and not _YEAR_RE.search(q):
        q = f"{q} {_CURRENT_YEAR}"
        transforms.append("added_fresh_year")

    if (
        _TECH_HINT.search(q)
        and "documentation" not in lowered
        and "docs" not in lowered
        and re.search(r"\b(api|sdk|usage|configure|install)\b", q, re.I)
    ):
        q = f"{q} official documentation"
        transforms.append("docs_hint")

    q = re.sub(r"\s+", " ", q).strip()
    if len(q) > _MAX_QUERY_LEN:
        q = q[:_MAX_QUERY_LEN].rsplit(" ", 1)[0]
        transforms.append("truncated")

    return q, transforms


def prepare_search_query(
    query: str,
    *,
    strict: bool | None = None,
) -> QueryPrepResult:
    """Validate and optimize a query. If strict and invalid, passed_gate=False."""
    original = query
    strict_mode = strict if strict is not None else strict_query_gate_enabled()
    hints: list[str] = []

    optimized, transforms = optimize_query_for_engine(query)
    if not optimized.strip():
        return QueryPrepResult(
            original=original,
            query="",
            passed_gate=False,
            reject_reason="Query empty after optimization.",
            hints=hints or ["Provide keyword-style query."],
        )

    # Re-validate optimized form
    ok2, reason2, hints2 = validate_query_quality(optimized)
    if not ok2 and strict_mode:
        if _has_korean(optimized) and len(optimized) >= _MIN_CHARS:
            return QueryPrepResult(
                original=original,
                query=optimized,
                passed_gate=True,
                transformations=transforms,
            )
        return QueryPrepResult(
            original=original,
            query=optimized,
            passed_gate=False,
            reject_reason=reason2,
            hints=hints2 or hints,
            transformations=transforms,
        )

    return QueryPrepResult(
        original=original,
        query=optimized,
        passed_gate=True,
        transformations=transforms,
    )


def format_query_rejection(prep: QueryPrepResult) -> str:
    """Agent-facing rejection block (host must rewrite query)."""
    lines = [
        "## [QUERY REJECTED] Not search-engine ready",
        "",
        f"**Your query:** `{prep.original[:200]}`",
        f"**Problem:** {prep.reject_reason}",
        "",
        "### Rewrite rules (mandatory)",
        "- Use **3–12 keywords**, not a chat sentence.",
        "- Include **library/product name** + **aspect** (API, install, CVE, vs, benchmark).",
        f"- Add **`{_CURRENT_YEAR}`** for version-sensitive tech.",
        "- Security topics: include `CVE` or `security advisory`.",
        "- Comparisons: include `vs` or `comparison`.",
        "- Do **not** pass the user's raw message — distill keywords first.",
        "",
        "### Templates",
    ]
    for h in prep.hints[:5]:
        lines.append(f"- {h}")
    lines.extend(
        [
            "",
            "Retry the same tool with a new `query=` string only.",
        ]
    )
    return "\n".join(lines)


def format_query_meta(prep: QueryPrepResult) -> str:
    """Footer when query was auto-optimized."""
    if not prep.transformations or prep.query.strip() == prep.original.strip():
        return ""
    return (
        f"\n_query: `{prep.original[:80]}` → `{prep.query[:80]}` "
        f"({', '.join(prep.transformations)})_"
    )
