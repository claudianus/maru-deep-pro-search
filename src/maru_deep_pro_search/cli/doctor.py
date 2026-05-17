"""Read-only setup diagnostics (duplicate protocol, stale hooks, legacy paths)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .agents.base import AgentAdapter
from .backup import read_text_safe
from .hooks_templates import hook_script_stale, is_managed_hook
from .prompts import PROTOCOL_START_MARKER
from .verify_status import verify_adapter


@dataclass
class Diagnosis:
    mcp_ok: bool
    rules_ok: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.mcp_ok and self.rules_ok and not self.warnings


def count_protocol_markers(text: str) -> int:
    return text.count(PROTOCOL_START_MARKER)


def _warn_duplicate_protocol(paths: list[tuple[Path, str]], warnings: list[str]) -> None:
    for path, label in paths:
        if not path.is_file():
            continue
        text = read_text_safe(path)
        count = count_protocol_markers(text)
        if count > 1:
            warnings.append(f"duplicate_protocol ({count} blocks in {label})")


def _warn_stale_hooks(paths: list[Path], warnings: list[str]) -> None:
    for path in paths:
        if not path.is_file():
            continue
        if hook_script_stale(path):
            if is_managed_hook(path):
                warnings.append(f"stale_hook {path.name}")
            else:
                warnings.append(f"stale_hook {path.name} (unmanaged — run setup --repair)")


def _legacy_project_scope_warnings(warnings: list[str]) -> None:
    legacy = [
        Path.cwd() / ".cursor" / "mcp.json",
        Path.cwd() / ".mcp.json",
        Path.cwd() / ".claude" / "settings.json",
    ]
    found = [str(p.relative_to(Path.cwd())) for p in legacy if p.is_file()]
    if found:
        warnings.append(f"warn_project_scope ({', '.join(found)})")


def protocol_check_paths(adapter: AgentAdapter) -> list[tuple[Path, str]]:
    home = Path.home()
    name = adapter.name
    paths: list[tuple[Path, str]] = []
    if name == "claude":
        paths.append((home / ".claude" / "CLAUDE.md", "CLAUDE.md"))
    elif name == "cursor":
        paths.append(
            (home / ".cursor" / "rules" / "maru-research-protocol.md", "maru-research-protocol.md")
        )
    elif name == "windsurf":
        paths.append(
            (
                home / ".windsurf" / "rules" / "maru-research-protocol.md",
                "maru-research-protocol.md",
            )
        )
    elif name == "aider":
        paths.append((home / ".aider" / "CONVENTIONS.md", "CONVENTIONS.md"))
    elif name == "copilot":
        paths.append(
            (
                home / ".copilot" / "instructions" / "maru-research-protocol.instructions.md",
                "maru-research-protocol.instructions.md",
            )
        )
    elif name == "continue":
        cfg = home / ".continue" / "config.yaml"
        if cfg.is_file():
            paths.append((cfg, "config.yaml rules"))
    elif name == "kimi":
        paths.append((home / ".kimi" / "config.toml", "config.toml"))
    elif name == "opencode":
        paths.append((home / ".config" / "opencode" / "AGENTS.md", "AGENTS.md"))
    elif name == "zed":
        paths.append((home / ".config" / "zed" / "assistant.md", "assistant.md"))
    elif name == "hermes":
        paths.append((home / ".hermes" / "SOUL.md", "SOUL.md"))
    elif name == "codex":
        paths.append((home / ".codex" / "AGENTS.md", "AGENTS.md"))
    return paths


def managed_hook_paths(adapter: AgentAdapter) -> list[Path]:
    home = Path.home()
    maru = home / ".maru"
    by_name: dict[str, list[Path]] = {
        "claude": [
            home / ".claude" / "hooks" / "maru_research_gate.py",
            home / ".claude" / "hooks" / "maru_research_revert.py",
            home / ".claude" / "hooks" / "maru_session_start.py",
        ],
        "windsurf": [maru / "windsurf_research_gate.py"],
        "kimi": [maru / "kimi_research_gate.py"],
        "aider": [maru / "aider_research_gate.py"],
    }
    return by_name.get(adapter.name, [])


def diagnose_adapter(adapter: AgentAdapter, scope: str = "user") -> Diagnosis:
    """Run extended read-only checks for one adapter."""
    base = verify_adapter(adapter, scope)
    warnings: list[str] = []
    if not base.get("mcp", True):
        warnings.append("mcp_missing")
    if not base.get("rules", True):
        warnings.append("rules_missing")

    _warn_duplicate_protocol(protocol_check_paths(adapter), warnings)
    _warn_stale_hooks(managed_hook_paths(adapter), warnings)
    if scope == "user":
        _legacy_project_scope_warnings(warnings)

    return Diagnosis(
        mcp_ok=bool(base.get("mcp", True)),
        rules_ok=bool(base.get("rules", True)),
        warnings=warnings,
    )


def format_diagnosis_line(display_name: str, diag: Diagnosis) -> tuple[bool, str]:
    parts: list[str] = []
    parts.append("MCP " + ("ok" if diag.mcp_ok else "MISSING"))
    parts.append("protocol " + ("ok" if diag.rules_ok else "MISSING"))
    warn = " | ".join(f"WARN {w}" for w in diag.warnings)
    if warn:
        parts.append(warn)
    line = f"{'✓' if diag.healthy else '✗'} {display_name} — {' | '.join(parts)}"
    return diag.healthy, line
