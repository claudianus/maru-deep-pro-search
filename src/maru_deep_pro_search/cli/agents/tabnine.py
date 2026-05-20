"""Tabnine adapter — privacy-focused AI coding assistant.

Official docs: https://docs.tabnine.com/main/getting-started/tabnine-agent/guidelines

Tabnine Agent uses Markdown guidelines stored in:
- Project:  .tabnine/guidelines/*.md
- Global:   ~/.tabnine/guidelines/*.md
"""

from __future__ import annotations

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


class TabnineAdapter(AgentAdapter):
    name = "tabnine"
    display_name = "Tabnine"

    def detect(self) -> bool:
        home = Path.home()
        vscode_ext = home / ".vscode" / "extensions"
        has_tabnine_ext = False
        if vscode_ext.exists():
            has_tabnine_ext = any(
                "tabnine" in p.name.lower() for p in vscode_ext.iterdir() if p.is_dir()
            )
        return home.joinpath(".tabnine").exists() or has_tabnine_ext

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".tabnine") / "config.json"
        return Path.home() / ".tabnine" / "config.json"

    def _guidelines_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".tabnine") / "guidelines"
        return Path.home() / ".tabnine" / "guidelines"

    def _skills_dir(self, scope: str) -> Path | None:
        return self._guidelines_dir(scope)

    skills_format = "flat"

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".tabnine") / "mcp_servers.json"
        return Path.home() / ".tabnine" / "mcp_servers.json"

    def backup(self) -> list[Path]:
        paths = [self._config_path("user"), self._mcp_path("user")]
        backups = [backup_file(p) for p in paths if p.exists()]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user"), self._mcp_path("user")]:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._mcp_path(scope)
        path.parent.mkdir(parents=True, exist_ok=True)
        config = read_json_safe(path)
        mcp_servers = config.get("mcpServers")
        if not isinstance(mcp_servers, dict):
            mcp_servers = {}
            config["mcpServers"] = mcp_servers
        mcp_servers["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. .tabnine/guidelines/*.md — official Tabnine format
        guidelines_dir = self._guidelines_dir(scope)
        guidelines_dir.mkdir(parents=True, exist_ok=True)

        rule_file = guidelines_dir / "maru-research-protocol.md"
        protocol = get_protocol_for_agent(self.name)

        content = read_text_safe(rule_file)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(rule_file, new_content)

        return True
