"""Kimi Code CLI adapter."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import (
    backup_file,
    read_json_safe,
    restore_file,
    write_json_safe,
)
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command


class KimiAdapter(AgentAdapter):
    name = "kimi"
    display_name = "Kimi Code CLI"

    def detect(self) -> bool:
        return shutil.which("kimi") is not None or Path.home().joinpath(".kimi").exists()

    def _mcp_path(self, scope: str) -> Path:
        return Path.home() / ".kimi" / "mcp.json"

    def _settings_path(self, scope: str) -> Path:
        return Path.home() / ".kimi" / "settings.json"

    def backup(self) -> list[Path]:
        paths = [self._mcp_path("user"), self._settings_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._mcp_path("user"), self._settings_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
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
        path = self._settings_path(scope)
        config = read_json_safe(path)

        protocol = get_protocol_for_agent(self.name)
        current = config.get("systemPrompt", "")
        new_prompt = inject_protocol(current, protocol)
        if new_prompt != current:
            config["systemPrompt"] = new_prompt
            write_json_safe(path, config)
        return True
