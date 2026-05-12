"""Windsurf adapter."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import (
    backup_file,
    read_json_safe,
    read_text_safe,
    restore_file,
    write_json_safe,
    write_text_safe,
)
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command


class WindsurfAdapter(AgentAdapter):
    name = "windsurf"
    display_name = "Windsurf"

    def detect(self) -> bool:
        return (
            Path(".windsurf").exists()
            or Path.home().joinpath(".windsurf").exists()
            or shutil.which("windsurf") is not None
        )

    def _mcp_path(self, scope: str) -> Path:
        # Official Windsurf MCP config path (per docs.windsurf.com)
        if scope == "project":
            return Path(".codeium") / "windsurf" / "mcp_config.json"
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    def _rules_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".windsurfrules")
        return Path.home() / ".windsurfrules"

    def _settings_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".windsurf") / "settings.json"
        return Path.home() / ".windsurf" / "settings.json"

    def backup(self) -> list[Path]:
        paths = [self._mcp_path("user"), self._rules_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._mcp_path("user"), self._rules_path("user")]:
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
        # 1. .windsurfrules
        path = self._rules_path(scope)
        content = read_text_safe(path)
        protocol = get_protocol_for_agent(self.name)

        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(path, new_content)

        # 2. .windsurf/settings.json — MCP auto-enable + research hints
        settings_path = self._settings_path(scope)
        settings = read_json_safe(settings_path)
        if "mcp" not in settings:
            settings["mcp"] = {}
        if "autoEnableTools" not in settings["mcp"]:
            settings["mcp"]["autoEnableTools"] = True
        if "agent" not in settings:
            settings["agent"] = {}
        settings["agent"]["defaultInstructions"] = (
            "You MUST call deep_research before any code generation, file edit, "
            "or architecture decision. This is enforced by the MCP server."
        )
        write_json_safe(settings_path, settings)

        return True
