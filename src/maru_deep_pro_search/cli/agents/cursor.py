"""Cursor adapter — supports .cursor/rules/*.md, .cursor/mcp.json, settings.json.

Cursor 2026+ deprecates `.cursorrules` in favor of `.cursor/rules/*.md` (or `.mdc`)
for project rules. User rules are managed via Cursor Settings → Rules UI.

Official docs: https://cursor.com/docs/rules
"""

from __future__ import annotations

import contextlib
import shutil
from pathlib import Path

from ..backup import (
    backup_file,
    read_json_safe,
    read_text_safe,
    restore_file,
    sorted_backup_paths,
    write_json_safe,
    write_text_safe,
)
from ..hooks_templates import template_body, write_managed_hook
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command


class CursorAdapter(AgentAdapter):
    name = "cursor"
    display_name = "Cursor"

    def detect(self) -> bool:
        return (
            Path.home().joinpath(".cursor").exists()
            or Path(".cursor").exists()
            or shutil.which("cursor") is not None
        )

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "mcp.json"
        return Path.home() / ".cursor" / "mcp.json"

    def _settings_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "settings.json"
        return Path.home() / ".cursor" / "settings.json"

    def _hooks_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "hooks.json"
        return Path.home() / ".cursor" / "hooks.json"

    def _rules_dir(self, scope: str) -> Path:
        """Cursor project rules directory — official since 2026."""
        if scope == "project":
            return Path(".cursor") / "rules"
        return Path.home() / ".cursor" / "rules"

    def _commands_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "commands"
        return Path.home() / ".cursor" / "commands"

    def _skills_dir(self, scope: str) -> Path | None:
        # https://cursor.com/docs/agent/chat/commands — skills live under ``.cursor/skills/``.
        if scope == "project":
            return Path(".cursor") / "skills"
        return Path.home() / ".cursor" / "skills"

    def backup(self) -> list[Path]:
        paths = [
            self._mcp_path("user"),
            self._settings_path("user"),
            self._hooks_path("user"),
        ]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [
            self._mcp_path("user"),
            self._settings_path("user"),
            self._hooks_path("user"),
        ]:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def refresh_managed_hooks(self, *, repair: bool = False) -> bool:
        gate_script = Path.home() / ".maru" / "cursor_research_gate.py"
        write_managed_hook(gate_script, template_body("cursor_research_gate"), force=repair)
        return True

    def _install_hooks(self, scope: str, *, repair: bool = False) -> None:
        """Install Cursor Lifecycle Hooks for research gating."""
        self.refresh_managed_hooks(repair=repair)
        gate_script = Path.home() / ".maru" / "cursor_research_gate.py"
        cmd = f"python3 {gate_script}"

        hooks_path = self._hooks_path(scope)
        hooks = read_json_safe(hooks_path)
        if "version" not in hooks:
            hooks["version"] = 1
        if "hooks" not in hooks:
            hooks["hooks"] = {}

        group = hooks["hooks"]
        for event in ("beforeShellExecution", "beforeMCPExecution"):
            if event not in group:
                group[event] = []
            existing_cmds = [h.get("command", "") for h in group[event]]
            if cmd not in existing_cmds:
                group[event].append({"command": cmd})

        write_json_safe(hooks_path, hooks)

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._mcp_path(scope)
        config = read_json_safe(path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)

        self._install_hooks(scope)
        return True

    def inject_rules(self, scope: str = "user", *, repair: bool = False) -> bool:
        # 1. .cursor/rules/*.mdc — official rule format (2026+)
        #    Always-write so the rule is present even if the file is new.
        rules_dir = self._rules_dir(scope)
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Clean up legacy .md rule file to avoid duplicate rules
        legacy_rule_file = rules_dir / "maru-research-protocol.md"
        if legacy_rule_file.exists():
            with contextlib.suppress(OSError):
                legacy_rule_file.unlink()

        rule_file = rules_dir / "maru-research-protocol.mdc"
        protocol = get_protocol_for_agent(self.name)

        mdc_header = """---
description: Mandatory research protocol for code/architecture work
globs: *
alwaysApply: true
---
"""
        content = read_text_safe(rule_file)
        if not content.startswith("---"):
            new_content = inject_protocol(mdc_header + content, protocol)
        else:
            new_content = inject_protocol(content, protocol)

        if new_content != content:
            write_text_safe(rule_file, new_content)

        # 2. .cursor/commands/*.json — Cursor slash commands (official since 0.45+)
        cmds_dir = self._commands_dir(scope)
        cmds_dir.mkdir(parents=True, exist_ok=True)

        _write_cursor_command(
            cmds_dir / "ask.json",
            name="ask",
            description="Answer a general web question with live sources",
            prompt=(
                'Call answer with the user\'s current question, mode="balanced". '
                "Use the returned evidence packet to answer directly with inline "
                "citations [1], [2]. Use this for current facts, prices, "
                "recommendations, and Korean consumer searches."
            ),
        )
        _write_cursor_command(
            cmds_dir / "search.json",
            name="search",
            description="Run targeted web search",
            prompt=(
                "Extract a concise keyword query from the user's request and call "
                "web_search. Return ranked sources with citation IDs and note which "
                "results should be fetched next."
            ),
        )
        _write_cursor_command(
            cmds_dir / "compare.json",
            name="compare",
            description="Run comparative parallel search",
            prompt=(
                "Convert the user's comparison into 2-5 independent keyword queries "
                "and call parallel_search with comparison_mode=true. Summarize the "
                "strongest evidence with citations."
            ),
        )
        _write_cursor_command(
            cmds_dir / "research.json",
            name="research",
            description="Run deep research before any code change",
            prompt=(
                "Before writing or modifying any code, you MUST extract 3-12 search "
                "keywords from the user's technical intent and run deep_research. "
                "Summarize findings and wait for user confirmation before proceeding. "
                "Use /ask for ordinary web questions."
            ),
        )
        _write_cursor_command(
            cmds_dir / "verify.json",
            name="verify",
            description="Verify research was completed for this session",
            prompt=(
                "Check if deep_research has been called in this session. "
                "If not, refuse to proceed and instruct the user to run /research first."
            ),
        )

        # 3. settings.json — single read/write for MCP auto-enable
        settings_path = self._settings_path(scope)
        settings = read_json_safe(settings_path)
        if "mcp" not in settings:
            settings["mcp"] = {}
        settings["mcp"]["autoEnableTools"] = True
        write_json_safe(settings_path, settings)

        # 4. hooks.json — register cursor pre-execution hooks
        self._install_hooks(scope, repair=repair)

        return True


def _write_cursor_command(path: Path, name: str, description: str, prompt: str) -> None:
    """Write a Cursor custom slash command definition."""
    import json as _json

    cmd = {"name": name, "description": description, "prompt": prompt}
    serialized = _json.dumps(cmd, indent=2) + "\n"
    existing: str | None = None
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            existing = None
    if existing != serialized:
        path.write_text(serialized, encoding="utf-8")
