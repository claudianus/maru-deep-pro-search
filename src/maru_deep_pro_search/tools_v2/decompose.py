"""Query decomposition tool for iterative research (Perplexity-style).

Breaks complex queries into sub-queries with intent detection, entity extraction,
and rule-based + optional LLM refinement.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Lazy refiner import — graceful degradation if unavailable
try:
    from ..refiner.engine import RefinerEngine

    _REFINER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _REFINER_AVAILABLE = False
    RefinerEngine = None  # type: ignore[misc,assignment]
    logger.debug("RefinerEngine unavailable; decomposition will use rule-based fallback")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SubQuery:
    """A single decomposed sub-query with rationale."""

    text: str
    reason: str


@dataclass
class DecompositionResult:
    """Full decomposition output."""

    intent: str
    complexity: str
    entities: list[str]
    sub_queries: list[SubQuery]
    approach: str


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: dict[str, list[str]] = {
    "comparison": [
        r"\bcompare\b",
        r"\bversus\b",
        r"\bvs\b",
        r"\b difference\b",
        r"\b pros? and cons?\b",
        r"\bbetter than\b",
        r"\bwhich is (better|faster|cheaper|stronger)\b",
    ],
    "code": [
        r"\bhow to (code|implement|write|build|create)\b",
        r"\bcode example\b",
        r"\bprogramming\b",
        r"\blibrary\b",
        r"\bapi\b",
        r"\bfunction\b",
        r"\bscript\b",
        r"\bpython\b|\bjavascript\b|\btypescript\b|\brust\b|\bgo\b|\bjava\b",
        r"\bregex\b",
        r"\bdebug\b",
    ],
    "news": [
        r"\blatest\b",
        r"\brecent\b",
        r"\bnews\b",
        r"\bupdate\b",
        r"\bhappening\b",
        r"\bcurrent events?\b",
        r"\bthis week\b",
        r"\bthis month\b",
        r"\btoday\b",
    ],
    "how_to": [
        r"^how (to|do|can|should) ",
        r"\bstep[- ]by[- ]step\b",
        r"\btutorial\b",
        r"\bguide\b",
        r"\binstructions?\b",
    ],
    "factual": [
        r"^what is\b",
        r"^who is\b",
        r"^when did\b",
        r"^where is\b",
        r"^why does\b",
        r"^how many\b",
        r"^how much\b",
        r"\bdefinition\b",
        r"\bmeaning of\b",
    ],
}


def _detect_intent(query: str) -> str:
    """Detect query intent from keyword patterns.

    Args:
        query: Raw user query.

    Returns:
        Intent label (comparison, code, news, how_to, factual, research).
    """
    lowered = query.lower()
    scores: dict[str, int] = {}
    for intent, patterns in _INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, lowered))
        if score:
            scores[intent] = score
    if not scores:
        return "research"
    return max(scores.items(), key=lambda item: item[1])[0]


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

# Simple regex-based entity extraction — fast and good enough for decomposition
_ENTITY_PATTERNS = [
    # Quoted phrases
    r'"([^"]{3,60})"',
    r"'([^']{3,60})'",
    # Title-cased sequences (probable proper nouns)
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b",
    # Acronyms
    r"\b([A-Z]{2,6})\b",
    # Version numbers / years
    r"\b(20\d{2})\b",
    r"\b(v?\d+\.\d+(?:\.\d+)?)\b",
    # Technical terms
    r"\b([a-z]+[A-Z][a-zA-Z]{2,})\b",  # camelCase
]


def _extract_entities(query: str) -> list[str]:
    """Extract candidate entities from the query.

    Args:
        query: Raw user query.

    Returns:
        Deduplicated list of extracted entities.
    """
    seen: set[str] = set()
    entities: list[str] = []
    for pattern in _ENTITY_PATTERNS:
        for match in re.finditer(pattern, query):
            entity = match.group(1).strip()
            if len(entity) < 2 or entity.lower() in {
                "the",
                "and",
                "for",
                "with",
                "how",
                "what",
                "when",
                "where",
                "why",
                "who",
            }:
                continue
            key = entity.lower()
            if key not in seen:
                seen.add(key)
                entities.append(entity)
    return entities


# ---------------------------------------------------------------------------
# Complexity scoring
# ---------------------------------------------------------------------------


def _assess_complexity(query: str, entity_count: int) -> str:
    """Assess query complexity based on length, entities, and operators.

    Args:
        query: Raw user query.
        entity_count: Number of extracted entities.

    Returns:
        Complexity label: low, medium, or high.
    """
    word_count = len(query.split())
    and_count = query.lower().count(" and ") + query.lower().count(" & ")
    or_count = query.lower().count(" or ") + query.lower().count(" | ")

    score = 0
    if word_count > 15:
        score += 1
    if entity_count >= 3:
        score += 1
    if and_count + or_count >= 2:
        score += 1
    if any(op in query for op in ("compare", "versus", "vs", "difference between")):
        score += 1

    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Rule-based decomposition
# ---------------------------------------------------------------------------


def _decompose_comparison(query: str, entities: list[str]) -> list[SubQuery]:
    """Decompose a comparison query."""
    # Try to find "X and Y" or "X vs Y"
    parts = re.split(r"\b(?:and|vs|versus|or)\b", query, flags=re.IGNORECASE)
    parts = [p.strip(" ?.,;:") for p in parts if p.strip()]
    if len(parts) >= 2:
        x, y = parts[0], parts[1]
        return [
            SubQuery(f"What is {x}?", f"Establish baseline understanding of {x}"),
            SubQuery(f"What is {y}?", f"Establish baseline understanding of {y}"),
            SubQuery(
                f"{x} vs {y} differences",
                "Direct comparison of key differentiators",
            ),
        ]
    # Fallback
    return [
        SubQuery(f"Overview of {query}", "General context"),
        SubQuery(f"Key aspects of {query}", "Break down components"),
    ]


def _decompose_how_to(query: str, entities: list[str]) -> list[SubQuery]:
    """Decompose a how-to query."""
    # Strip leading "how to" / "how do I"
    topic = re.sub(r"^how\s+(?:to|do\s+i|can\s+i|should\s+i)\s+", "", query, flags=re.IGNORECASE)
    topic = topic.strip(" ?.,;:")
    return [
        SubQuery(f"What is {topic}?", "Understand the subject before attempting"),
        SubQuery(f"{topic} prerequisites", "List requirements and dependencies"),
        SubQuery(f"{topic} step by step", "Detailed implementation instructions"),
    ]


def _decompose_news(query: str, entities: list[str]) -> list[SubQuery]:
    """Decompose a news/current-events query."""
    topic = query
    for prefix in ["latest news about", "recent", "latest", "news about", "updates on"]:
        topic = re.sub(rf"^{prefix}\s+", "", topic, flags=re.IGNORECASE)
    topic = topic.strip(" ?.,;:")
    return [
        SubQuery(
            f"{topic} recent developments",
            "Catch up on the latest events and announcements",
        ),
        SubQuery(
            f"{topic} 2024 2025",
            "Context from the last two years for temporal grounding",
        ),
    ]


def _decompose_code(query: str, entities: list[str]) -> list[SubQuery]:
    """Decompose a code/programming query."""
    # Try to extract language or framework
    lang_match = re.search(
        r"\b(python|javascript|typescript|rust|go|java|c\+\+|c#|ruby|php)\b",
        query,
        re.IGNORECASE,
    )
    lang = (lang_match.group(1).capitalize() if lang_match else "") + " " if lang_match else ""

    # Strip language name to get the actual task
    task = query
    if lang_match:
        task = re.sub(rf"\b{lang_match.group(1)}\b", "", task, flags=re.IGNORECASE)
    task = re.sub(r"^how\s+(?:to|do\s+i|can\s+i)\s+", "", task, flags=re.IGNORECASE)
    task = task.strip(" ?.,;:")

    return [
        SubQuery(
            f"{lang}best practices for {task}",
            "Establish idiomatic approach before implementation",
        ),
        SubQuery(
            f"{lang}{task} code example",
            "Concrete implementation reference",
        ),
        SubQuery(
            f"{lang}common {task} pitfalls",
            "Avoid typical mistakes and edge cases",
        ),
    ]


def _decompose_factual(query: str, entities: list[str]) -> list[SubQuery]:
    """Decompose a factual / definitional query."""
    return [
        SubQuery(f"Definition and overview of {query}", "Core concept explanation"),
        SubQuery(f"Key facts about {query}", "Important details and statistics"),
        SubQuery(f"Real-world examples of {query}", "Concrete applications or instances"),
    ]


def _decompose_research(query: str, entities: list[str]) -> list[SubQuery]:
    """Decompose a general research query."""
    sub_queries: list[SubQuery] = [
        SubQuery(f"Overview of {query}", "Broad context and background"),
    ]
    if entities:
        for ent in entities[:2]:
            sub_queries.append(
                SubQuery(
                    f"Detailed information about {ent}",
                    f"Deep dive into key entity: {ent}",
                )
            )
    sub_queries.append(
        SubQuery(f"Current state and future of {query}", "Trends and forward-looking analysis"),
    )
    return sub_queries


# ---------------------------------------------------------------------------
# LLM refiner (optional)
# ---------------------------------------------------------------------------


async def _llm_refine_sub_queries(
    query: str,
    intent: str,
    entities: list[str],
    rule_based: list[SubQuery],
) -> list[SubQuery]:
    """Use the refiner LLM to improve sub-queries.

    Args:
        query: Original query.
        intent: Detected intent.
        entities: Extracted entities.
        rule_based: Sub-queries from rule-based decomposition.

    Returns:
        Refined sub-queries, or the original list if refiner is unavailable.
    """
    if not _REFINER_AVAILABLE or RefinerEngine is None:
        return rule_based

    refiner: Any
    try:
        refiner = RefinerEngine()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialise RefinerEngine: %s", exc)
        return rule_based

    prompt = (
        f"Original query: {query}\n"
        f"Detected intent: {intent}\n"
        f"Entities: {', '.join(entities) or 'none'}\n\n"
        "The following sub-queries were generated by a rule-based system. "
        "Improve them for better search results. Return ONLY a numbered list, "
        "one per line, in the format: NUMBER. SUB_QUERY | REASON\n\n"
        + "\n".join(f"{i + 1}. {sq.text} | {sq.reason}" for i, sq in enumerate(rule_based))
    )

    try:
        refined_text = await refiner.refine_content(
            text=prompt,
            query=query,
            max_tokens=1500,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Refiner failed during decomposition: %s", exc)
        return rule_based

    if not refined_text or not refined_text.strip():
        return rule_based

    # Parse the refiner output
    refined: list[SubQuery] = []
    for line in refined_text.strip().splitlines():
        line = line.strip()
        if not line or not re.match(r"^\d+\.", line):
            continue
        # Remove leading number
        body = re.sub(r"^\d+\.\s*", "", line)
        if "|" in body:
            text, reason = body.split("|", 1)
            refined.append(SubQuery(text.strip(), reason.strip()))
        else:
            refined.append(SubQuery(body, "Refined by LLM"))

    return refined if refined else rule_based


# ---------------------------------------------------------------------------
# Research strategy generator
# ---------------------------------------------------------------------------


def _generate_approach(intent: str, complexity: str, entity_count: int) -> str:
    """Generate a suggested research strategy.

    Args:
        intent: Detected query intent.
        complexity: Complexity label.
        entity_count: Number of extracted entities.

    Returns:
        Markdown paragraph with research strategy.
    """
    strategies: dict[str, str] = {
        "comparison": (
            "Start with independent overviews of each subject, "
            "then run a targeted comparison query. "
            "Cross-reference findings to identify bias."
        ),
        "code": (
            "Review best-practice documentation first, "
            "then inspect working code examples. "
            "Finally, check for common pitfalls and security considerations."
        ),
        "news": (
            "Search recent sources first for the latest developments, "
            "then broaden to the last two years for context. "
            "Prioritise primary sources (press releases, official blogs)."
        ),
        "how_to": (
            "Understand the core concept, list prerequisites, "
            "then follow step-by-step guides. "
            "Verify each step against multiple sources."
        ),
        "factual": (
            "Begin with authoritative definitions, "
            "then gather supporting facts and real-world examples. "
            "Cross-check statistics with primary data sources."
        ),
        "research": (
            "Start with a broad overview to map the landscape, "
            "then deep-dive into the most relevant entities. "
            "Finish with trend analysis for forward-looking insight."
        ),
    }
    base = strategies.get(intent, strategies["research"])

    if complexity == "high":
        base += (
            " Due to high complexity, iterate in multiple passes — "
            "narrow scope after each round of results."
        )
    elif complexity == "medium" and entity_count >= 2:
        base += (
            " With multiple key entities, consider parallel sub-queries "
            "to reduce total research time."
        )

    return base


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _format_result(result: DecompositionResult) -> str:
    """Format decomposition result into the required markdown output.

    Args:
        result: DecompositionResult dataclass.

    Returns:
        Markdown string matching the specification.
    """
    lines: list[str] = [
        "## Query Analysis",
        f"_intent: {result.intent} | complexity: {result.complexity} | entities: {result.entities}_",
        "",
        "### Sub-Queries",
    ]
    for i, sq in enumerate(result.sub_queries, start=1):
        lines.append(f"[{i}] {sq.text} — _reason: {sq.reason}_")
    lines.extend(["", "### Suggested Approach", result.approach])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def tool_decompose(
    query: str,
    mode: str = "standard",
) -> str:
    """Decompose a complex query into sub-queries.

    Detects intent, extracts entities, assesses complexity, and generates
    targeted sub-queries via rule-based heuristics.  If the refiner LLM is
    available the sub-queries are optionally polished for better search
    coverage.

    Args:
        query: The original user query.
        mode: Decomposition mode.  Currently only "standard" is supported;
            reserved for future variants (e.g. "aggressive", "minimal").

    Returns:
        Markdown formatted decomposition with analysis, sub-queries, and
        suggested research strategy.
    """
    if not query or not query.strip():
        return "## Query Analysis\n_intent: none | complexity: low | entities: []_\n\nNo query provided."

    clean_query = query.strip()
    intent = _detect_intent(clean_query)
    entities = _extract_entities(clean_query)
    complexity = _assess_complexity(clean_query, len(entities))

    # Rule-based decomposition
    if intent == "comparison":
        rule_based = _decompose_comparison(clean_query, entities)
    elif intent == "how_to":
        rule_based = _decompose_how_to(clean_query, entities)
    elif intent == "news":
        rule_based = _decompose_news(clean_query, entities)
    elif intent == "code":
        rule_based = _decompose_code(clean_query, entities)
    elif intent == "factual":
        rule_based = _decompose_factual(clean_query, entities)
    else:
        rule_based = _decompose_research(clean_query, entities)

    # Optional LLM refinement (async, non-blocking)
    if _REFINER_AVAILABLE and mode == "standard":
        try:
            sub_queries = await asyncio.wait_for(
                _llm_refine_sub_queries(clean_query, intent, entities, rule_based),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("LLM refinement timed out; using rule-based sub-queries")
            sub_queries = rule_based
    else:
        sub_queries = rule_based

    approach = _generate_approach(intent, complexity, len(entities))

    result = DecompositionResult(
        intent=intent,
        complexity=complexity,
        entities=entities,
        sub_queries=sub_queries,
        approach=approach,
    )
    return _format_result(result)
