"""Search query sanitizer: removes stale years from LLM-generated queries.

LLMs often include outdated years (2024, 2023) in search queries based on
their training data cutoff. This module automatically replaces stale years
with "latest" or the current year, ensuring fresh search results.
"""

from __future__ import annotations

import datetime
import re


def _current_year() -> int:
    """Return the current calendar year."""
    return datetime.datetime.now().year


# Module-level cache: (year, compiled_pattern)
_stale_year_pattern_cache: tuple[int, re.Pattern | None] = (0, None)


def _stale_year_pattern(current_year: int) -> re.Pattern:
    """Build a regex that matches years older than current_year - 1.

    For 2026, stale years are 2024 and earlier.
    Result is cached and refreshed when the year changes.
    """
    global _stale_year_pattern_cache
    cached_year, cached_pattern = _stale_year_pattern_cache
    if cached_year == current_year and cached_pattern is not None:
        return cached_pattern

    stale_threshold = current_year - 1  # 2025 is still acceptable in 2026
    # Match 4-digit years from 1900 up to stale_threshold
    stale_years = "|".join(str(y) for y in range(1900, stale_threshold + 1))
    pattern = re.compile(rf"\b({stale_years})\b")
    _stale_year_pattern_cache = (current_year, pattern)
    return pattern


# Common phrases that indicate a stale year reference
_STALE_PHRASES = [
    r"\bin\s+\d{4}\b",
    r"\bas\s+of\s+\d{4}\b",
    r"\bsince\s+\d{4}\b",
    r"\bfrom\s+\d{4}\b",
    r"\buntil\s+\d{4}\b",
    r"\bbefore\s+\d{4}\b",
    r"\bafter\s+\d{4}\b",
]


def sanitize_query(query: str, current_year: int | None = None) -> str:
    """Remove or replace stale years from a search query.

    Stale years (older than current_year - 1) are replaced with "latest"
    when they appear alone, or with the current year when part of a range.

    Examples:
        "React best practices 2024" → "React best practices latest"
        "Next.js 14 vs 15 2023" → "Next.js 14 vs 15 latest"
        "AI regulation 2024 2025" → "AI regulation 2025 2026"
        "Python features in 2024" → "Python features in latest"
        "solid state battery latest 2026" → "solid state battery latest 2026" (unchanged)
    """
    if not query or not query.strip():
        return query

    year = current_year or _current_year()
    stale_pattern = _stale_year_pattern(year)

    result = query.strip()

    # Replace standalone stale years with "latest"
    def _replace_year(match: re.Match) -> str:
        matched_year = int(match.group(1))
        if matched_year >= year:
            return str(match.group(0))  # Keep current/future years
        return "latest"

    result = stale_pattern.sub(_replace_year, result)  # type: ignore[no-any-return]

    # Clean up double "latest" occurrences
    result = re.sub(r"\blatest\s+latest\b", "latest", result, flags=re.IGNORECASE)
    result = re.sub(r"\blatest\s+(\d{4})\b", r"\1", result, flags=re.IGNORECASE)

    # Replace stale phrases like "in 2024" → "in latest"
    for phrase_pattern in _STALE_PHRASES:
        result = re.sub(
            phrase_pattern,
            lambda m: re.sub(r"\d{4}", "latest", m.group(0)),
            result,
            flags=re.IGNORECASE,
        )

    # Final cleanup: dedupe spaces and duplicate "latest"
    result = re.sub(r"\blatest\s+latest\b", "latest", result, flags=re.IGNORECASE)
    result = re.sub(r"\s+", " ", result).strip()

    return result


def sanitize_queries(queries: list[str], current_year: int | None = None) -> list[str]:
    """Sanitize multiple queries at once."""
    return [sanitize_query(q, current_year) for q in queries]
