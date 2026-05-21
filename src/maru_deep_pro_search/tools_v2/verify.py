"""Cross-source verification and conflict detection for the MCP server redesign.

Extracts claims from multiple sources, normalizes them, and compares across
sources to find verified facts, conflicts, and gaps in coverage.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VerifiedClaim:
    """A normalized claim extracted from a source with verification metadata."""

    claim: str
    source_indices: list[int] = field(default_factory=list)
    confidence: float = 0.0
    topic: str = ""


@dataclass
class Conflict:
    """A detected conflict between two claims."""

    claim_a: VerifiedClaim
    claim_b: VerifiedClaim
    severity: str = "HIGH"
    reason: str = ""


def _normalize_claim(claim: str) -> str:
    """Normalize a claim string for comparison.

    Args:
        claim: Raw claim text.

    Returns:
        Normalized lowercase string with punctuation removed and spaces
        collapsed.
    """
    normalized = claim.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _jaccard_similarity(a: str, b: str) -> float:
    """Calculate Jaccard similarity between two token sets.

    Args:
        a: First string.
        b: Second string.

    Returns:
        Jaccard similarity score (0.0–1.0).
    """
    set_a = set(a.split())
    set_b = set(b.split())
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return intersection / union


def _embedding_similarity(a: str, b: str) -> float:
    """Calculate embedding-based similarity (simplified fallback).

    Uses a weighted combination of Jaccard token similarity and character-
    level bigram overlap. This avoids heavy embedding model dependencies while
    still catching semantic paraphrases that pure token matching misses.

    Args:
        a: First normalized string.
        b: Second normalized string.

    Returns:
        Similarity score (0.0–1.0).
    """
    jaccard = _jaccard_similarity(a, b)

    def _bigrams(s: str) -> set[str]:
        return {s[i : i + 2] for i in range(len(s) - 1)}

    bigrams_a = _bigrams(a)
    bigrams_b = _bigrams(b)
    if not bigrams_a or not bigrams_b:
        char_sim = 0.0
    else:
        intersection = len(bigrams_a & bigrams_b)
        union = len(bigrams_a | bigrams_b)
        char_sim = intersection / union if union > 0 else 0.0

    return 0.6 * jaccard + 0.4 * char_sim


def _extract_claims(source: dict[str, Any], source_index: int) -> list[VerifiedClaim]:
    """Extract claims from a single source dictionary.

    Args:
        source: Source dictionary. May contain 'content' (raw text) or
            'claims' (pre-extracted list). Optional 'topic' key sets the
            claim topic.
        source_index: 1-based index of this source for attribution.

    Returns:
        List of VerifiedClaim objects extracted from the source.
    """
    claims: list[VerifiedClaim] = []

    if "claims" in source:
        for claim_text in source["claims"]:
            claims.append(
                VerifiedClaim(
                    claim=str(claim_text),
                    source_indices=[source_index],
                    topic=source.get("topic", ""),
                )
            )
        return claims

    content = source.get("content", "")
    if not content:
        return claims

    sentences = re.split(r"(?<=[.!?])\s+", content)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 20:
            claims.append(
                VerifiedClaim(
                    claim=sentence,
                    source_indices=[source_index],
                    topic=source.get("topic", ""),
                )
            )

    return claims


def _compare_claims(
    claim1: VerifiedClaim,
    claim2: VerifiedClaim,
    exact_threshold: float = 0.95,
    fuzzy_threshold: float = 0.75,
) -> tuple[float, str]:
    """Compare two claims and return similarity score and match type.

    Args:
        claim1: First claim.
        claim2: Second claim.
        exact_threshold: Minimum similarity for an exact match.
        fuzzy_threshold: Minimum similarity for a fuzzy match.

    Returns:
        Tuple of (similarity_score, match_type) where match_type is one of
        'exact', 'fuzzy', or 'none'.
    """
    norm1 = _normalize_claim(claim1.claim)
    norm2 = _normalize_claim(claim2.claim)

    if norm1 == norm2:
        return 1.0, "exact"

    jaccard = _jaccard_similarity(norm1, norm2)
    if jaccard >= exact_threshold:
        return jaccard, "exact"

    embedding_sim = _embedding_similarity(norm1, norm2)
    if embedding_sim >= fuzzy_threshold:
        return embedding_sim, "fuzzy"

    best_score = max(jaccard, embedding_sim)
    return best_score, "fuzzy" if best_score >= fuzzy_threshold else "none"


def _merge_claims(claims: list[VerifiedClaim]) -> list[VerifiedClaim]:
    """Merge duplicate claims across sources.

    Args:
        claims: List of extracted claims (potentially with duplicates).

    Returns:
        Deduplicated list with merged source indices.
    """
    merged: list[VerifiedClaim] = []

    for claim in claims:
        found = False
        for existing in merged:
            score, match_type = _compare_claims(claim, existing)
            if match_type in ("exact", "fuzzy"):
                existing.source_indices = sorted(
                    set(existing.source_indices + claim.source_indices)
                )
                existing.confidence = max(existing.confidence, claim.confidence)
                found = True
                break

        if not found:
            merged.append(claim)

    return merged


def _detect_conflicts(
    claims: list[VerifiedClaim],
    conflict_threshold: float = 0.3,
    min_similarity: float = 0.5,
) -> list[Conflict]:
    """Detect conflicts between claims from different sources.

    Two claims are flagged as conflicting when they are on a similar topic
    (above min_similarity) but do not agree enough to be merged (below
    conflict_threshold in similarity). The closer they are, the higher the
    severity.

    Args:
        claims: Deduplicated list of claims.
        conflict_threshold: Upper similarity bound for a conflict.
        min_similarity: Lower similarity bound to consider claims related.

    Returns:
        List of detected Conflict objects.
    """
    conflicts: list[Conflict] = []

    for i, claim1 in enumerate(claims):
        for claim2 in claims[i + 1 :]:
            if set(claim1.source_indices) & set(claim2.source_indices):
                continue

            score, _ = _compare_claims(claim1, claim2)

            if score < min_similarity:
                continue

            if score < conflict_threshold:
                if score < 0.4:
                    severity = "HIGH"
                elif score < 0.55:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                conflicts.append(
                    Conflict(
                        claim_a=claim1,
                        claim_b=claim2,
                        severity=severity,
                        reason=(
                            f"Similar claims with contradictory details (similarity: {score:.2f})"
                        ),
                    )
                )

    return conflicts


def _calculate_confidence(claim: VerifiedClaim, total_sources: int) -> float:
    """Calculate confidence score for a single claim.

    Confidence increases with the fraction of sources that contain the claim
    and gets a small boost when 2+ or 3+ independent sources agree.

    Args:
        claim: The claim to score.
        total_sources: Total number of input sources.

    Returns:
        Confidence score (0.0–1.0).
    """
    source_count = len(claim.source_indices)
    coverage = source_count / total_sources if total_sources > 0 else 0.0

    base = min(1.0, coverage * 0.8 + 0.2)

    if source_count >= 3:
        base = min(1.0, base + 0.15)
    elif source_count >= 2:
        base = min(1.0, base + 0.08)

    return base


def _identify_gaps(
    claims: list[VerifiedClaim],
    sources: list[dict[str, Any]],
) -> list[str]:
    """Identify topics or claims needing more verification.

    Args:
        claims: Final deduplicated claims.
        sources: Original source dictionaries.

    Returns:
        List of gap descriptions.
    """
    gaps: list[str] = []

    source_topics: set[str] = set()
    for source in sources:
        topic = source.get("topic", "")
        if topic:
            source_topics.add(topic)

    for topic in source_topics:
        topic_claims = [c for c in claims if c.topic == topic]
        if len(topic_claims) < 2:
            gaps.append(f"Insufficient claims for topic: {topic}")

    for claim in claims:
        if claim.confidence < 0.5:
            truncated = claim.claim[:60] + "..." if len(claim.claim) > 60 else claim.claim
            gaps.append(f"Low confidence claim: {truncated}")

    return gaps


def _format_verification_report(
    claims: list[VerifiedClaim],
    conflicts: list[Conflict],
    gaps: list[str],
    overall_confidence: float,
    total_sources: int,
) -> str:
    """Format the verification report as markdown.

    Args:
        claims: Final deduplicated claims with confidence scores.
        conflicts: Detected conflicts.
        gaps: Identified gaps.
        overall_confidence: Average confidence across all claims.
        total_sources: Total number of input sources.

    Returns:
        Markdown formatted verification report.
    """
    lines: list[str] = []

    lines.append("## Verification Report")
    lines.append(f"_sources: {total_sources} | overall_confidence: {overall_confidence:.2f}_")
    lines.append("")

    lines.append("### ✅ Verified Facts")
    verified = [c for c in claims if c.confidence >= 0.6]
    if verified:
        for i, claim in enumerate(verified, 1):
            sources_str = ", ".join(str(s) for s in sorted(claim.source_indices))
            lines.append(
                f"[{i}] {claim.claim} "
                f"(confidence: {claim.confidence:.2f}, sources: [{sources_str}])"
            )
    else:
        lines.append("No sufficiently verified facts found.")
    lines.append("")

    lines.append("### ⚠️ Conflicts")
    if conflicts:
        for conflict in conflicts:
            lines.append(
                f"[{conflict.severity}] {conflict.claim_a.claim} vs {conflict.claim_b.claim}"
            )
            if conflict.reason:
                lines.append(f"  _Reason: {conflict.reason}_")
    else:
        lines.append("No conflicts detected.")
    lines.append("")

    lines.append("### 🔍 Gaps")
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- No significant gaps identified.")

    return "\n".join(lines)


async def tool_verify(
    sources: list[dict[str, Any]],
) -> str:
    """Cross-verify facts across multiple sources and detect conflicts.

    Extracts claims from each source, normalizes them, and compares across
    sources using exact matching, fuzzy Jaccard similarity, and embedding-
    based similarity. Detects conflicts between contradictory claims and
    assigns confidence scores based on source coverage and agreement.

    Args:
        sources: List of source dictionaries, each containing at least a
            'content' key. Optional keys include 'claims' (pre-extracted
            claims list), 'topic' (topic/category), and 'url'/'title'.

    Returns:
        Markdown formatted verification report with verified facts,
        conflicts, and gaps.
    """
    if not sources:
        return (
            "## Verification Report\n"
            "_sources: 0 | overall_confidence: 0.00_\n\n"
            "No sources provided."
        )

    all_claims: list[VerifiedClaim] = []
    for i, source in enumerate(sources):
        claims = _extract_claims(source, i + 1)
        all_claims.extend(claims)

    if not all_claims:
        return (
            "## Verification Report\n"
            f"_sources: {len(sources)} | overall_confidence: 0.00_\n\n"
            "No extractable claims found in sources."
        )

    merged_claims = _merge_claims(all_claims)

    for claim in merged_claims:
        claim.confidence = _calculate_confidence(claim, len(sources))

    conflicts = _detect_conflicts(merged_claims)
    gaps = _identify_gaps(merged_claims, sources)

    overall_confidence = (
        sum(c.confidence for c in merged_claims) / len(merged_claims) if merged_claims else 0.0
    )

    return _format_verification_report(
        merged_claims,
        conflicts,
        gaps,
        overall_confidence,
        len(sources),
    )
