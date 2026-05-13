"""Content extraction utilities for LLM-optimized output."""

from __future__ import annotations

import re


def truncate_for_llm(text: str, max_tokens: int = 2500) -> str:
    """Truncate text to approximate token limit, respecting boundaries.

    Tries to cut at paragraph, then sentence, then word boundaries.
    Approximates 1 token ≈ 4 characters.
    """
    if not text:
        return ""

    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text

    # Try paragraph boundary
    truncated = text[:max_chars]
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.7:
        return text[:last_para].strip() + "\n\n...[truncated]"

    # Try sentence boundary
    last_sentence = truncated.rfind(". ")
    if last_sentence > max_chars * 0.7:
        return text[: last_sentence + 1].strip() + "\n\n...[truncated]"

    # Try word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        return text[:last_space].strip() + " ...[truncated]"

    return text[:max_chars].strip() + "...[truncated]"


def extract_code_blocks(markdown: str) -> list[dict]:
    """Extract code blocks from markdown."""
    blocks = []
    pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(markdown):
        blocks.append(
            {
                "language": match.group(1) or "text",
                "code": match.group(2).strip(),
            }
        )
    return blocks


def extract_headings(markdown: str) -> list[dict]:
    """Extract headings from markdown."""
    headings = []
    for line in markdown.split("\n"):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            headings.append(
                {
                    "level": len(match.group(1)),
                    "text": match.group(2).strip(),
                }
            )
    return headings


def estimate_token_count(text: str) -> int:
    """Estimate token count (very rough: ~4 chars per token)."""
    return len(text) // 4
