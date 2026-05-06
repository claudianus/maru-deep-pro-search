"""Code-aware content analysis for coding-agent-optimized research.

Adds code block language detection, API signature extraction, code-to-text ratio
scoring, and content freshness assessment on top of extracted page content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Language signatures — fast regex over full lexer
# ═══════════════════════════════════════════════════════════════

_LANG_SIGNATURES: list[tuple[str, re.Pattern]] = [
    ("python", re.compile(r"\b(def |class |import |from \w+ import|async def |await |elif |__init__|self\.)", re.MULTILINE)),
    ("python", re.compile(r"\b(print\(|range\(|len\(|enumerate\(|zip\(|lambda |f\"|f')", re.MULTILINE)),
    ("javascript", re.compile(r"\b(const |let |var |function |=> |require\(|module\.exports|\.then\(|async await)", re.MULTILINE)),
    ("typescript", re.compile(r"\b(interface |type \w+ =|: string|: number|: boolean|: void|as const|readonly )", re.MULTILINE)),
    ("jsx", re.compile(r"<(div|span|button|input|form|View|Text|Component)[\s/>]", re.MULTILINE)),
    ("go", re.compile(r"\b(func |package |go func|defer |fmt\.|\.Error\(|:= )", re.MULTILINE)),
    ("rust", re.compile(r"\b(fn |let mut |impl |pub fn|use std::|\.unwrap\(|\.await|match |Some\()", re.MULTILINE)),
    ("java", re.compile(r"\b(public class|public static void|import java\.|System\.out|\.equals\(|ArrayList<)", re.MULTILINE)),
    ("shell", re.compile(r"^[#$] |\b(apt-get|npm |yarn |pip |docker |kubectl|git |curl |wget)\b", re.MULTILINE)),
    ("sql", re.compile(r"\b(SELECT |FROM |WHERE |INSERT INTO|CREATE TABLE|ALTER TABLE|JOIN |GROUP BY)", re.MULTILINE | re.IGNORECASE)),
    ("json", re.compile(r'^\s*[\[{].*[\]}]\s*$', re.MULTILINE | re.DOTALL)),
    ("yaml", re.compile(r"^\w+:\s", re.MULTILINE)),
    ("css", re.compile(r"[.#][\w-]+\s*\{|@media |@import |font-size|background-color|margin:|padding:", re.MULTILINE)),
    ("html", re.compile(r"<!DOCTYPE|<html|<head|<body|<div|<script>|<link ", re.MULTILINE | re.IGNORECASE)),
    ("markdown", re.compile(r"^#{1,6} |^\- \[[ x]\] |\[.*\]\(.*\)", re.MULTILINE)),
]


def detect_language(code: str) -> str:
    """Detect programming language from a code snippet using fast signature matching."""
    if not code or len(code.strip()) < 10:
        return "text"

    # Strip common prefixes that confuse detection
    stripped = code.strip()
    if stripped.startswith("$ "):
        return "shell"

    scores: dict[str, int] = {}
    for lang, pattern in _LANG_SIGNATURES:
        matches = len(pattern.findall(stripped))
        if matches:
            scores[lang] = scores.get(lang, 0) + matches

    if not scores:
        return "text"

    return max(scores, key=lambda k: scores[k])


# ═══════════════════════════════════════════════════════════════
# API signature extraction
# ═══════════════════════════════════════════════════════════════

_API_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Python: def name(args), class Name(Base):
    ("python", re.compile(r"^\s*(async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(->\s*\S+)?\s*:", re.MULTILINE)),
    ("python", re.compile(r"^\s*class\s+(\w+)\s*(\(([^)]*)\))?\s*:", re.MULTILINE)),
    # Python: @decorator
    ("python", re.compile(r"^\s*@(\w+)", re.MULTILINE)),
    # JS/TS: function/const/class declarations
    ("javascript", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)),
    ("javascript", re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", re.MULTILINE)),
    # Go: func Name(args) returnType
    ("go", re.compile(r"func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(([^)]*)\)\s*(\([^)]*\)|[\w\[\]]*)", re.MULTILINE)),
    # Rust: fn name(args) -> Type
    ("rust", re.compile(r"(?:pub\s+)?fn\s+(\w+)\s*(?:<[^>]+>)?\s*\(([^)]*)\)\s*(->\s*\S+)?", re.MULTILINE)),
    # Java: public/private Type methodName(args)
    ("java", re.compile(r"(?:public|private|protected)\s+(?:static\s+)?(?:<[^>]+>\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)),
    # Import statements (all languages)
    ("python", re.compile(r"^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$", re.MULTILINE)),
    ("javascript", re.compile(r"^\s*(?:import\s+.*?\s+from\s+['\"](\S+)['\"]|require\(['\"](\S+)['\"]\))", re.MULTILINE)),
    ("go", re.compile(r"^\s*import\s+(?:\(\s*)?\"([^\"]+)\"", re.MULTILINE)),
]


def extract_api_signatures(markdown: str, max_signatures: int = 20) -> list[dict]:
    """Extract API signatures (function defs, class defs, imports) from markdown."""
    signatures: list[dict] = []

    for lang, pattern in _API_PATTERNS:
        for match in pattern.finditer(markdown):
            if len(signatures) >= max_signatures:
                break
            groups = match.groups()
            signatures.append({
                "language": lang,
                "signature": match.group(0).strip(),
                "name": groups[1] if len(groups) > 1 else "",
            })

    return signatures[:max_signatures]


# ═══════════════════════════════════════════════════════════════
# Code-aware statistics
# ═══════════════════════════════════════════════════════════════

@dataclass
class CodeAwareStats:
    """Code-aware content analysis results."""
    code_block_count: int = 0
    code_languages: list[str] = field(default_factory=list)
    code_total_chars: int = 0
    text_total_chars: int = 0
    code_to_text_ratio: float = 0.0
    api_signatures: list[dict] = field(default_factory=list)
    primary_language: str = ""
    is_api_reference: bool = False
    is_tutorial: bool = False
    is_error_solution: bool = False
    published_date: str = ""
    freshness_days: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "code_block_count": self.code_block_count,
            "code_languages": self.code_languages,
            "code_to_text_ratio": round(self.code_to_text_ratio, 2),
            "api_signatures": self.api_signatures[:10],
            "primary_language": self.primary_language,
            "is_api_reference": self.is_api_reference,
            "is_tutorial": self.is_tutorial,
            "is_error_solution": self.is_error_solution,
            "published_date": self.published_date,
            "freshness_days": self.freshness_days,
        }


def analyze_code_content(markdown: str, published_date: str = "") -> CodeAwareStats:
    """Analyze extracted markdown for code-aware statistics."""
    stats = CodeAwareStats(published_date=published_date)

    # Extract code blocks
    code_blocks = re.findall(r"```(\w+)?\s*\n(.*?)```", markdown, re.DOTALL)
    languages: list[str] = []

    for lang_hint, code in code_blocks:
        stats.code_block_count += 1
        stats.code_total_chars += len(code)

        if lang_hint and lang_hint != "text":
            languages.append(lang_hint)
        else:
            detected = detect_language(code)
            if detected != "text":
                languages.append(detected)

    # Count unique languages
    from collections import Counter
    lang_counts = Counter(languages)
    stats.code_languages = [lang for lang, _ in lang_counts.most_common(5)]
    stats.primary_language = stats.code_languages[0] if stats.code_languages else ""

    # Text content (excluding code blocks)
    text_only = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    stats.text_total_chars = len(text_only.strip())

    # Code-to-text ratio
    total = stats.code_total_chars + stats.text_total_chars
    if total > 0:
        stats.code_to_text_ratio = stats.code_total_chars / total

    # API signatures
    stats.api_signatures = extract_api_signatures(markdown)

    # Content classification
    heading_text = markdown[:500].lower()
    stats.is_api_reference = bool(
        stats.code_block_count >= 3 and stats.api_signatures
        and any(kw in heading_text for kw in ["reference", "api", "module", "function", "class", "method", "interface"])
    )
    stats.is_tutorial = bool(
        stats.code_block_count >= 2
        and any(kw in heading_text for kw in ["tutorial", "guide", "how to", "getting started", "walkthrough", "introduction"])
    )
    stats.is_error_solution = bool(
        any(kw in markdown[:1000].lower() for kw in ["error", "exception", "traceback", "solution", "fixed", "solved"])
    )

    # Freshness
    if published_date:
        try:
            pub_date = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now - pub_date.replace(tzinfo=timezone.utc)
            stats.freshness_days = delta.days
        except (ValueError, TypeError):
            pass

    return stats
