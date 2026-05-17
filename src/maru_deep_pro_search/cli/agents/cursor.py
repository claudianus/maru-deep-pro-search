"""Cursor adapter — supports .cursor/rules/*.md, .cursor/mcp.json, settings.json.

Cursor 2026+ deprecates `.cursorrules` in favor of `.cursor/rules/*.md` (or `.mdc`)
for project rules. User rules are managed via Cursor Settings → Rules UI.

Official docs: https://cursor.com/docs/rules
"""

from __future__ import annotations

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
        paths = [self._mcp_path("user"), self._settings_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._mcp_path("user"), self._settings_path("user")]:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._mcp_path(scope)
        config = read_json_safe(path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. .cursor/rules/*.md — official rule format (2026+)
        #    Always-write so the rule is present even if the file is new.
        rules_dir = self._rules_dir(scope)
        rules_dir.mkdir(parents=True, exist_ok=True)
        rule_file = rules_dir / "maru-research-protocol.md"
        protocol = get_protocol_for_agent(self.name)

        content = read_text_safe(rule_file)
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

        return True


def _write_cursor_command(path: Path, name: str, description: str, prompt: str) -> None:
    """Write a Cursor custom slash command definition."""
    cmd = {"name": name, "description": description, "prompt": prompt}
    import json as _json

    if not path.exists() or _json.loads(path.read_text()).get("prompt") != prompt:
        path.write_text(_json.dumps(cmd, indent=2) + "\n")
