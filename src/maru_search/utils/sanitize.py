"""Sanitize fetched content before injecting into LLM context.

Prevents prompt injection, jailbreak attempts, and system prompt leakage
via malicious web content."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Zero-width and invisible characters that can hide malicious text
_ZERO_WIDTH_CHARS = re.compile(
    "[\u200b\u200c\u200d\u2060\ufeff\u180e]"
)

# Control characters (except common whitespace)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")

# Chat format tokens used by major LLMs to delineate roles
_CHAT_TOKENS = re.compile(
    r"<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>"
    r"|<s>|</s>|<\|endoftext\|>|<\|begin_of_text\|>|<\|end_of_text\|>",
    re.IGNORECASE,
)

# Suspicious instruction-override patterns (case-insensitive)
_SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+(instructions?|commands?)", re.I),
    re.compile(r"ignore\s+above\s+(instructions?|commands?)", re.I),
    re.compile(r"you\s+are\s+now\s+(a\s+)?DAN", re.I),
    re.compile(r"do\s+anything\s+now", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"reveal\s+your\s+(system\s+)?prompt", re.I),
    re.compile(r"===?\s*SYSTEM\s*===?", re.I),
    re.compile(r"===?\s*INSTRUCTION\s*===?", re.I),
    re.compile(r"new\s+instruction\s*:", re.I),
    re.compile(r"from\s+now\s+on\s*,?\s*you\s+(will|must|are)", re.I),
    re.compile(r"disregard\s+(all\s+)?previous\s+(instructions?|commands?)", re.I),
    re.compile(r"forget\s+(all\s+)?previous\s+(instructions?|commands?)", re.I),
]

# Maximum length of a single suspicious match to report
_MAX_REPORT_LEN = 80


def sanitize_for_llm(text: str) -> str:
    """Sanitize text before injecting into LLM context.

    Steps:
    1. Remove zero-width characters that can hide text
    2. Remove control characters
    3. Neutralize chat format tokens
    4. Detect and flag suspicious instruction-override patterns

    Returns sanitized text with warning markers if suspicious content
    was detected.
    """
    if not text:
        return text

    original_len = len(text)

    # Step 1: Remove zero-width characters
    text = _ZERO_WIDTH_CHARS.sub("", text)

    # Step 2: Remove control characters
    text = _CONTROL_CHARS.sub("", text)

    # Step 3: Neutralize chat format tokens by breaking them
    text = _CHAT_TOKENS.sub(lambda m: m.group(0).replace("<", "‹").replace(">", "›"), text)

    # Step 4: Detect suspicious patterns
    detected: list[str] = []
    for pattern in _SUSPICIOUS_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0)[:_MAX_REPORT_LEN]
            detected.append(snippet)

    if detected:
        # Replace suspicious patterns with neutralized versions
        for pattern in _SUSPICIOUS_PATTERNS:
            text = pattern.sub(lambda m: "[⚠️ SUSPICIOUS CONTENT REMOVED]", text)

        logger.warning(
            "Detected %d suspicious pattern(s) in fetched content: %s",
            len(detected),
            detected[:3],
        )

    # Log if significant stripping occurred
    stripped = original_len - len(text)
    if stripped > 100:
        logger.debug("Stripped %d characters from content", stripped)

    return text


def sanitize_search_results(text: str) -> str:
    """Wrapper for search result output sanitization.

    Adds a boundary marker so the LLM can clearly distinguish
    external content from system instructions.
    """
    text = sanitize_for_llm(text)
    # Prepend a clear boundary marker
    return text
