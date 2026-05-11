"""Cline adapter — VS Code extension AI agent."""

from __future__ import annotations

import shutil
from pathlib import Path

from .base import AgentAdapter
from ..backup import backup_file, read_text_safe, restore_file, write_text_safe
from ..prompts import get_protocol_for_agent


class ClineAdapter(AgentAdapter):
    name = "cline"
    display_name = "Cline"

    def detect(self) -> bool:
        return (
            Path.home().joinpath(".vscode", "extensions", "saoudrizwan.claude-dev").exists()
            or Path.home().joinpath(".vscode", "extensions", "claude-dev").exists()
            or shutil.which("cline") is not None
        )

    def _rules_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".clinerules")
        return Path.home() / ".clinerules"

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cline", "mcp.json")
        return Path.home() / ".cline" / "mcp.json"

    def backup(self) -> list[Path]:
        paths = [self._rules_path("user"), self._mcp_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._rules_path("user"), self._mcp_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        from ..backup import read_json_safe, write_json_safe

        path = self._mcp_path(scope)
        config = read_json_safe(path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["maru-deep-pro-search"] = {
            "command": "python3",
            "args": ["-m", "maru_deep_pro_search.server"],
        }
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        path = self._rules_path(scope)
        content = read_text_safe(path)
        protocol = get_protocol_for_agent(self.name)

        if protocol in content:
            return True

        write_text_safe(path, content + "\n\n# maru-deep-pro-search Research Protocol\n\n" + protocol + "\n")
        return True
