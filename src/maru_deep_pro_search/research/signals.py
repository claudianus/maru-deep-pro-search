"""Source-quality signals shared by ranking, planning, and receipts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .expander import extract_keywords

_PAYWALL_DOMAINS = {
    "medium.com",
    "towardsdatascience.com",
    "substack.com",
    "forbes.com",
    "wired.com",
    "wsj.com",
    "nytimes.com",
    "technologyreview.com",
    "ieee.org",
    "dl.acm.org",
}

_DYNAMIC_DOMAINS = {
    "dev.to",
    "hashnode.dev",
    "notion.site",
}

_PAYWALL_TEXT = re.compile(
    r"\b(member[- ]only|members[- ]only|subscribe|subscription|sign in to read|"
    r"log in to read|continue reading|metered|paywall|join .* to read|"
    r"get unlimited access|unlock this article)\b",
    re.I,
)
_BLOCKED_TEXT = re.compile(
    r"\b(access denied|forbidden|captcha|cloudflare|enable javascript|"
    r"checking your browser|access blocked|request blocked|403 forbidden|"
    r"403 error|http 403|too many requests)\b",
    re.I,
)
_LOW_VALUE_TITLE = re.compile(
    r"\b(homepage|home page|buying guide|best laptops?|deals?|price|shop|"
    r"download now|login|sign up)\b",
    re.I,
)
_TECH_QUERY = re.compile(
    r"\b(api|benchmark|breaking|compatibility|cve|docs?|github|library|"
    r"llm|mcp|patch|performance|release|security|transformers|comfyui)\b",
    re.I,
)
_KOREAN_NLP_QUERY = re.compile(
    r"(한국어|카카오톡|감정|텍스트|초경량|분류|koelectra|kcelectra|kobert|nsmc)",
    re.I,
)
_GENERIC_KOREAN_LANGUAGE_DOMAIN = {
    "en.m.wiktionary.org",
    "en.wiktionary.org",
    "ko.m.wikipedia.org",
    "ko.wikipedia.org",
    "en.m.wikipedia.org",
    "en.wikipedia.org",
    "namu.wiki",
    "branah.com",
    "languages.oup.com",
}

FOCUS_ALIAS_MARKERS = (
    "koelectra",
    "kcelectra",
    "kr-electra",
    "korelectra",
    "kobert",
    "korsts",
    "nsmc",
    "kakao",
    "kakaotalk",
    "sentiment",
    "toxicity",
    "comfyui",
    "transformers",
    "huggingface",
)


@dataclass(frozen=True)
class SourceSignals:
    """Computed signals for a source relative to a query."""

    query_coverage: float = 0.0
    exact_entity_hits: int = 0
    required_entity_count: int = 0
    missing_entities: list[str] = field(default_factory=list)
    access_risk: str = "open"
    access_reasons: list[str] = field(default_factory=list)
    noise_penalty: float = 0.0
    proximity_boost: float = 0.0


def _norm_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[-_/.:]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _domain(url: str) -> str:
    candidate = url.strip()
    parsed = urlparse(candidate)
    if not parsed.netloc and "://" not in candidate and not candidate.startswith(("/", "#")):
        parsed = urlparse(f"//{candidate}")
    host = parsed.hostname or parsed.netloc.rsplit("@", 1)[-1].split(":", 1)[0]
    return host.lower().removeprefix("www.").rstrip(".")


def source_mentions_focus_alias(text: str) -> bool:
    """Return whether text mentions a shared high-value research alias."""
    haystack = _norm_text(text)
    return any(
        _contains_normalized_term(haystack, _norm_text(marker)) for marker in FOCUS_ALIAS_MARKERS
    )


def _contains_normalized_term(haystack: str, term: str) -> bool:
    if not term:
        return False
    return re.search(rf"(?<![a-z0-9가-힣]){re.escape(term)}(?![a-z0-9가-힣])", haystack) is not None


def required_entities(query: str) -> list[str]:
    """Extract years, versions, CVEs, hardware specs, and digit-bearing model names."""
    entities: list[str] = []
    entities.extend(re.findall(r"CVE-\d{4}-\d+", query, flags=re.I))
    entities.extend(re.findall(r"\bv?\d+\.\d+(?:\.\d+)?\b", query, flags=re.I))
    entities.extend(re.findall(r"\b20\d{2}\b", query))
    entities.extend(re.findall(r"\b\d+\s?GB\b", query, flags=re.I))
    entities.extend(re.findall(r"\bM\d+(?:\s?(?:Pro|Max|Ultra))?\b", query, flags=re.I))
    entities.extend(re.findall(r"\b[A-Za-z][A-Za-z0-9._+-]*\d[A-Za-z0-9._+-]*\b", query))

    seen: set[str] = set()
    unique: list[str] = []
    for entity in entities:
        normalized = _norm_text(entity)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(entity)
    return unique


def classify_access(
    url: str,
    *,
    title: str = "",
    snippet: str = "",
    content: str = "",
    content_length: int | None = None,
) -> tuple[str, list[str]]:
    """Classify whether a source is likely open, paywalled, dynamic, or blocked."""
    domain = _domain(url)
    haystack = f"{title}\n{snippet}\n{content}"[:8000]
    reasons: list[str] = []

    if _BLOCKED_TEXT.search(haystack):
        reasons.append("blocked/anti-bot text")
        return "blocked_likely", reasons

    if _PAYWALL_TEXT.search(haystack):
        reasons.append("paywall wording")
        return "paywall_likely", reasons

    if any(domain == d or domain.endswith("." + d) for d in _PAYWALL_DOMAINS):
        reasons.append("known paywall domain")
        if content_length is not None and content_length < 2500:
            return "paywall_likely", reasons
        return "paywall_possible", reasons

    if any(domain == d or domain.endswith("." + d) for d in _DYNAMIC_DOMAINS):
        reasons.append("dynamic article domain")
        if content_length is not None and content_length < 1200:
            return "dynamic_likely", reasons
        return "open", reasons

    return "open", reasons


def query_coverage(query: str, title: str, snippet: str, url: str) -> float:
    """Compute weighted keyword coverage for a source against the query."""
    terms = list(dict.fromkeys(extract_keywords(query)))
    alias_terms: list[str] = []
    lower_query = query.lower()
    if any(token in lower_query for token in ("한국어", "카카오톡", "감정", "텍스트", "초경량")):
        alias_terms = list(dict.fromkeys([*FOCUS_ALIAS_MARKERS, "korean", "huggingface"]))
    if not terms:
        return 0.0

    title_norm = _norm_text(title)
    snippet_norm = _norm_text(snippet)
    url_norm = _norm_text(url)

    def _term_score(term: str) -> float:
        term_norm = _norm_text(term)
        if not term_norm:
            return 0.0
        if _contains_normalized_term(title_norm, term_norm):
            return 1.0
        if _contains_normalized_term(url_norm, term_norm):
            return 0.8
        if _contains_normalized_term(snippet_norm, term_norm):
            return 0.65
        return 0.0

    score = 0.0
    for term in terms:
        score += _term_score(term)

    alias_hits = sum(1 for term in alias_terms if _term_score(term) > 0)
    alias_bonus = min(alias_hits * 0.08, 0.24)
    return min((score / len(terms)) + alias_bonus, 1.0)


def _entity_hits(query: str, haystack: str) -> tuple[int, int, list[str]]:
    entities = required_entities(query)
    if not entities:
        return 0, 0, []

    normalized_text = _norm_text(haystack)
    hits = 0
    missing: list[str] = []
    for entity in entities:
        normalized_entity = _norm_text(entity)
        if _contains_normalized_term(normalized_text, normalized_entity):
            hits += 1
        else:
            missing.append(entity)
    return hits, len(entities), missing


def _noise_penalty(query: str, title: str, snippet: str, url: str, coverage: float) -> float:
    domain = _domain(url)
    path = urlparse(url).path.strip("/")
    haystack = f"{title} {snippet} {url}"
    penalty = 0.0

    if coverage < 0.2:
        penalty += 1.4
    if coverage < 0.35 and _TECH_QUERY.search(query) and _LOW_VALUE_TITLE.search(haystack):
        penalty += 2.2
    if not path and coverage < 0.45:
        penalty += 1.0
    if "search" in path.lower() and coverage < 0.6:
        penalty += 0.8
    if domain in {"geeksforgeeks.org", "tutorialspoint.com", "w3schools.com"}:
        penalty += 0.6
    if _KOREAN_NLP_QUERY.search(query):
        if domain in _GENERIC_KOREAN_LANGUAGE_DOMAIN:
            penalty += 4.0
        if not source_mentions_focus_alias(haystack) and not re.search(
            r"(텍스트|감정|분류|대화|모델|nlp|hugging ?face)", haystack, re.I
        ):
            penalty += 1.4
    return penalty


def source_signals(query: str, title: str, snippet: str, url: str) -> SourceSignals:
    """Return all lightweight quality signals for a search result."""
    coverage = query_coverage(query, title, snippet, url)
    haystack = f"{title}\n{snippet}\n{url}"
    entity_hits, entity_count, missing = _entity_hits(query, haystack)
    access_risk, access_reasons = classify_access(url, title=title, snippet=snippet)
    penalty = _noise_penalty(query, title, snippet, url, coverage)

    if entity_count:
        missing_ratio = len(missing) / entity_count
        penalty += missing_ratio * 0.9

    boost = 0.0
    if coverage >= 0.75:
        boost += 2.0
    elif coverage >= 0.55:
        boost += 1.2
    elif coverage >= 0.4:
        boost += 0.5
    if entity_count:
        boost += min(entity_hits * 0.45, 1.4)
    if re.search(r"\b(benchmark|release notes|changelog|docs?|github|paper)\b", haystack, re.I):
        boost += 0.4
    if _KOREAN_NLP_QUERY.search(query) and source_mentions_focus_alias(haystack):
        boost += 1.0

    return SourceSignals(
        query_coverage=round(coverage, 3),
        exact_entity_hits=entity_hits,
        required_entity_count=entity_count,
        missing_entities=missing,
        access_risk=access_risk,
        access_reasons=access_reasons,
        noise_penalty=round(penalty, 3),
        proximity_boost=round(boost, 3),
    )
