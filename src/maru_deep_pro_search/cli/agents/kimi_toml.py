"""Idempotent TOML edits for Kimi ``config.toml``."""

from __future__ import annotations

import re

from ..toml_edit import (
    has_nested_key,
    insert_root_block,
    key_at_root,
    remove_toml_key,
)

KIMI_SYSTEM_MARKER = "# MARU-SYSTEM-PROMPT"
KIMI_HOOK_MARKER = "# MARU-KIMI-HOOK"

_HOOK_BLOCK_RE = re.compile(
    re.escape(KIMI_HOOK_MARKER) + r"\n\[\[hooks\]\].*?(?=\n# |\n\[\[hooks\]\]|\Z)",
    re.DOTALL,
)


def system_prompt_at_root(lines: list[str]) -> bool:
    """True when ``system_prompt`` sits before the first TOML table."""
    return key_at_root(lines, "system_prompt")


def has_nested_system_prompt(lines: list[str]) -> bool:
    """True when ``system_prompt`` was appended inside a TOML table."""
    return has_nested_key(lines, "system_prompt")


def upsert_kimi_system_prompt(text: str, protocol: str) -> str:
    """Insert or replace the MARU-managed ``system_prompt`` block at TOML root."""
    block_lines = [
        KIMI_SYSTEM_MARKER,
        'system_prompt = """',
        protocol.strip(),
        '"""',
    ]
    lines = text.splitlines() if text else []
    lines = [ln for ln in lines if ln.strip() != KIMI_SYSTEM_MARKER]
    lines = remove_toml_key(lines, "system_prompt")
    lines = insert_root_block(lines, ["", *block_lines])
    return "\n".join(lines).rstrip() + "\n"


def upsert_kimi_hook_block(text: str, hook_block: str) -> str:
    """Insert or replace the MARU PreToolUse hook (no duplicate ``[[hooks]]``)."""
    if "kimi_research_gate.py" in text and KIMI_HOOK_MARKER not in text:
        return text
    block = f"{KIMI_HOOK_MARKER}\n{hook_block.strip()}"
    if KIMI_HOOK_MARKER in text:
        return _HOOK_BLOCK_RE.sub(block, text)
    return f"{text.rstrip()}\n\n{block}\n"


def upsert_default_yolo_false(text: str) -> str:
    """Ensure ``default_yolo = false`` exists at TOML root for the research gate."""
    lines = text.splitlines() if text else []
    if key_at_root(lines, "default_yolo"):
        return text
    lines = remove_toml_key(lines, "default_yolo")
    lines = insert_root_block(
        lines,
        ["", "# MARU: disable auto-approve so research gate works", "default_yolo = false"],
    )
    return "\n".join(lines).rstrip() + "\n"
