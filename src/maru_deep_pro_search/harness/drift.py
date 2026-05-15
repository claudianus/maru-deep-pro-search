"""Workspace drift detection — dependency manifest changes since last research.

No network, no LLM: compares hashes of a small allowlist of manifest files.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

# Cap bytes read per file to keep I/O bounded on large lockfiles.
_MAX_BYTES = 8192

WATCH_FILES: tuple[str, ...] = (
    "pyproject.toml",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
)

_ERROR_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ModuleNotFoundError:\s*\S+", re.I),
    re.compile(r"ImportError:\s*.+", re.I),
    re.compile(r"SyntaxError:\s*.+", re.I),
    re.compile(r"TypeError:\s*.+", re.I),
    re.compile(r"AttributeError:\s*.+", re.I),
    re.compile(r"DeprecationWarning:\s*.+", re.I),
    re.compile(r"\bCVE-\d{4}-\d+\b", re.I),
    re.compile(r"No module named\s+'[^']+'", re.I),
)


@dataclass
class WorkspaceSnapshot:
    """Per-file content fingerprints at a point in time."""

    root: str
    files: dict[str, str] = field(default_factory=dict)

    def fingerprint(self) -> str:
        h = hashlib.sha256()
        for name in sorted(self.files):
            h.update(name.encode())
            h.update(self.files[name].encode())
        return h.hexdigest()[:16]


def workspace_root() -> Path:
    return Path.cwd()


def _file_hash(path: Path) -> str:
    data = path.read_bytes()[:_MAX_BYTES]
    return hashlib.sha256(data).hexdigest()[:12]


def snapshot_workspace(root: Path | None = None) -> WorkspaceSnapshot:
    """Hash allowlisted manifest files under *root* (default: cwd)."""
    base = (root or workspace_root()).resolve()
    files: dict[str, str] = {}
    for name in WATCH_FILES:
        path = base / name
        if path.is_file():
            try:
                files[name] = _file_hash(path)
            except OSError:
                continue
    return WorkspaceSnapshot(root=str(base), files=files)


def compare_snapshots(
    baseline: WorkspaceSnapshot, current: WorkspaceSnapshot | None = None
) -> list[str]:
    """Return human-readable drift reasons (empty if none)."""
    current = current or snapshot_workspace(Path(baseline.root) if baseline.root else None)
    reasons: list[str] = []
    all_names = set(baseline.files) | set(current.files)
    for name in sorted(all_names):
        old = baseline.files.get(name)
        new = current.files.get(name)
        if old == new:
            continue
        if old is None:
            reasons.append(f"`{name}` added")
        elif new is None:
            reasons.append(f"`{name}` removed")
        else:
            reasons.append(f"`{name}` modified")
    return reasons


def extract_error_signature(text: str) -> str:
    """Stable short hash for the first actionable error line in tool output."""
    if not text or len(text) < 8:
        return ""
    for pattern in _ERROR_PATTERNS:
        match = pattern.search(text)
        if match:
            line = match.group(0).strip()[:200]
            return hashlib.sha256(line.encode()).hexdigest()[:12]
    return ""


def suggest_research_queries(
    drift_reasons: list[str],
    last_query: str,
    error_line: str = "",
) -> list[str]:
    """Heuristic micro-queries for the host LLM (no local synthesis)."""
    suggestions: list[str] = []
    if error_line:
        suggestions.append(f"{error_line} fix 2026")
    for reason in drift_reasons:
        if "pyproject.toml" in reason or "uv.lock" in reason:
            suggestions.append(f"{last_query} dependency version latest")
            suggestions.append("python package security advisory latest")
            break
        if "package.json" in reason or "lock" in reason:
            suggestions.append(f"{last_query} npm package latest version")
            break
    if not suggestions and drift_reasons:
        suggestions.append(f"{last_query} latest changes best practices")
    return suggestions[:3]


def format_drift_warning(
    drift_reasons: list[str],
    suggestions: list[str],
    *,
    error_drift: bool = False,
) -> str:
    """Markdown appendix for tool responses."""
    lines = [
        "",
        "🟠 **Research drift detected** — workspace changed since your last `deep_research`.",
        "",
    ]
    if drift_reasons:
        lines.append("**Manifest changes:**")
        for r in drift_reasons:
            lines.append(f"- {r}")
        lines.append("")
    if error_drift:
        lines.append("**New error pattern** detected in a recent tool result.")
        lines.append("")
    if suggestions:
        lines.append("**Suggested `deep_research` queries (host decides):**")
        for s in suggestions:
            lines.append(f"- `{s}`")
        lines.append("")
    lines.append("_Call `drift_status` for details without re-searching the web._")
    return "\n".join(lines)
