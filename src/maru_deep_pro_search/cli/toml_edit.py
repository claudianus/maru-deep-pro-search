"""Shared line-based TOML helpers for agent config adapters."""

from __future__ import annotations


def first_table_header_index(lines: list[str]) -> int:
    """Index of the first TOML table header, or ``len(lines)`` if none."""
    for i, line in enumerate(lines):
        if line.strip().startswith("["):
            return i
    return len(lines)


def insert_root_block(lines: list[str], block: list[str]) -> list[str]:
    """Insert *block* at root level (before the first ``[table]`` header)."""
    idx = first_table_header_index(lines)
    return lines[:idx] + block + lines[idx:]


def remove_toml_key(lines: list[str], key: str) -> list[str]:
    """Remove *key* assignments (including multiline strings) from TOML lines."""
    result: list[str] = []
    state = "normal"  # normal | in_ml_double | in_ml_single
    prefix = f"{key}"
    for line in lines:
        stripped = line.strip()
        if state == "normal":
            if stripped.startswith(prefix):
                rest = stripped.split("=", 1)[1].strip() if "=" in stripped else ""
                if rest.startswith('"""'):
                    if rest.endswith('"""') and len(rest) > 3:
                        continue
                    state = "in_ml_double"
                    continue
                if rest.startswith("'''"):
                    if rest.endswith("'''") and len(rest) > 3:
                        continue
                    state = "in_ml_single"
                    continue
                continue
            result.append(line)
        elif state == "in_ml_double":
            if stripped.endswith('"""'):
                state = "normal"
        elif state == "in_ml_single":
            if stripped.endswith("'''"):
                state = "normal"
    return result


def key_at_root(lines: list[str], key: str) -> bool:
    """True when *key* appears before the first TOML table header."""
    first_table = first_table_header_index(lines)
    return any(line.strip().startswith(key) for line in lines[:first_table])


def has_nested_key(lines: list[str], key: str) -> bool:
    """True when *key* exists but not at root level."""
    has_key = any(line.strip().startswith(key) for line in lines)
    return has_key and not key_at_root(lines, key)
