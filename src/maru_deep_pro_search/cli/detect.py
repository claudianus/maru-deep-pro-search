"""Auto-detect installed AI agents on the user's machine."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

AgentDetector = Callable[[], bool]


# ── Claude Code ──────────────────────────────────────────────
def _detect_claude_code() -> bool:
    return (
        shutil.which("claude") is not None
        or Path.home().joinpath(".claude.json").exists()
        or Path.home().joinpath(".claude").exists()
    )


# ── Cursor ───────────────────────────────────────────────────
def _detect_cursor() -> bool:
    return (
        Path.home().joinpath(".cursor").exists()
        or Path(".cursor").exists()
        or shutil.which("cursor") is not None
    )


# ── Kimi Code CLI ────────────────────────────────────────────
def _detect_kimi() -> bool:
    return (
        shutil.which("kimi") is not None
        or Path.home().joinpath(".kimi").exists()
    )


# ── AntiGravity ──────────────────────────────────────────────
def _detect_antigravity() -> bool:
    return Path.home().joinpath(".gemini", "antigravity").exists()


# ── Kilo Code ────────────────────────────────────────────────
def _detect_kilo() -> bool:
    return (
        Path.home().joinpath(".config", "kilo").exists()
        or shutil.which("kilo") is not None
    )


# ── OpenCode ─────────────────────────────────────────────────
def _detect_opencode() -> bool:
    return (
        shutil.which("opencode") is not None
        or Path.home().joinpath(".config", "opencode").exists()
    )


# ── Windsurf ─────────────────────────────────────────────────
def _detect_windsurf() -> bool:
    return (
        Path(".windsurf").exists()
        or Path.home().joinpath(".windsurf").exists()
        or shutil.which("windsurf") is not None
    )


# ── Aider ────────────────────────────────────────────────────
def _detect_aider() -> bool:
    return shutil.which("aider") is not None


# ── GitHub Copilot ───────────────────────────────────────────
def _detect_copilot() -> bool:
    return (
        shutil.which("code") is not None
        or shutil.which("gh") is not None
        or Path.home().joinpath(".vscode", "extensions").exists()
    )


# ── Continue ─────────────────────────────────────────────────
def _detect_continue() -> bool:
    return (
        Path.home().joinpath(".continue", "config.json").exists()
        or Path.home().joinpath(".config", "continue", "config.json").exists()
    )


# ── Cline ────────────────────────────────────────────────────
def _detect_cline() -> bool:
    return (
        Path.home().joinpath(".vscode", "extensions", "saoudrizwan.claude-dev").exists()
        or Path.home().joinpath(".vscode", "extensions", "claude-dev").exists()
    )


# ── Zed ──────────────────────────────────────────────────────
def _detect_zed() -> bool:
    return (
        shutil.which("zed") is not None
        or Path.home().joinpath(".config", "zed").exists()
        or Path.home().joinpath(".zed").exists()
    )


# ── JetBrains AI ─────────────────────────────────────────────
def _detect_jetbrains() -> bool:
    home = Path.home()
    jetbrains_dirs = list(home.glob(".jetbrains*")) + list(home.glob("Library/Application Support/JetBrains*"))
    return bool(
        shutil.which("idea") or shutil.which("webstorm") or shutil.which("pycharm")
        or jetbrains_dirs
    )


# ── Supermaven ───────────────────────────────────────────────
def _detect_supermaven() -> bool:
    return (
        shutil.which("supermaven") is not None
        or Path.home().joinpath(".supermaven").exists()
    )


# ── Cody (Sourcegraph) ───────────────────────────────────────
def _detect_cody() -> bool:
    home = Path.home()
    vscode_ext = home / ".vscode" / "extensions"
    has_cody_ext = False
    if vscode_ext.exists():
        has_cody_ext = any(
            "sourcegraph" in p.name.lower()
            for p in vscode_ext.iterdir()
            if p.is_dir()
        )
    return (
        shutil.which("cody") is not None
        or home.joinpath(".config", "cody").exists()
        or has_cody_ext
    )


# ── Codeium ──────────────────────────────────────────────────
def _detect_codeium() -> bool:
    home = Path.home()
    vscode_ext = home / ".vscode" / "extensions"
    has_codeium_ext = False
    if vscode_ext.exists():
        has_codeium_ext = any(
            "codeium" in p.name.lower()
            for p in vscode_ext.iterdir()
            if p.is_dir()
        )
    return (
        shutil.which("codeium") is not None
        or home.joinpath(".codeium").exists()
        or has_codeium_ext
    )


# ── Amazon Q Developer ───────────────────────────────────────
def _detect_amazon_q() -> bool:
    home = Path.home()
    vscode_ext = home / ".vscode" / "extensions"
    has_q_ext = False
    if vscode_ext.exists():
        has_q_ext = any(
            p.name.startswith("amazon-q")
            for p in vscode_ext.iterdir()
            if p.is_dir()
        )
    return (
        shutil.which("q") is not None
        or home.joinpath(".aws", "amazonq").exists()
        or has_q_ext
    )


# ── Devin ────────────────────────────────────────────────────
def _detect_devin() -> bool:
    return (
        shutil.which("devin") is not None
        or Path.home().joinpath(".devin").exists()
        or Path(".devin").exists()
    )


# ── Tabnine ──────────────────────────────────────────────────
def _detect_tabnine() -> bool:
    home = Path.home()
    vscode_ext = home / ".vscode" / "extensions"
    has_tabnine_ext = False
    if vscode_ext.exists():
        has_tabnine_ext = any(
            "tabnine" in p.name.lower()
            for p in vscode_ext.iterdir()
            if p.is_dir()
        )
    return (
        home.joinpath(".tabnine").exists()
        or has_tabnine_ext
    )


# ── Hermes (Nous Research) ───────────────────────────────────
def _detect_hermes() -> bool:
    return (
        shutil.which("hermes") is not None
        or Path.home().joinpath(".hermes").exists()
    )


# ── Registry ─────────────────────────────────────────────────
AGENT_DETECTORS: dict[str, AgentDetector] = {
    "claude": _detect_claude_code,
    "cursor": _detect_cursor,
    "kimi": _detect_kimi,
    "antigravity": _detect_antigravity,
    "kilo": _detect_kilo,
    "opencode": _detect_opencode,
    "windsurf": _detect_windsurf,
    "aider": _detect_aider,
    "copilot": _detect_copilot,
    "continue": _detect_continue,
    "cline": _detect_cline,
    "zed": _detect_zed,
    "jetbrains": _detect_jetbrains,
    "supermaven": _detect_supermaven,
    "cody": _detect_cody,
    "codeium": _detect_codeium,
    "amazon_q": _detect_amazon_q,
    "devin": _detect_devin,
    "tabnine": _detect_tabnine,
    "hermes": _detect_hermes,
}


def detect_agents() -> dict[str, bool]:
    """Return a map of agent_name -> installed for all known agents."""
    return {name: fn() for name, fn in AGENT_DETECTORS.items()}


def installed_agents() -> list[str]:
    """Return only the names of agents that are installed."""
    return [name for name, detected in detect_agents().items() if detected]
