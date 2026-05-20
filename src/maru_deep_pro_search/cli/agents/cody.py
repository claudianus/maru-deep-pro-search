"""Cody (Sourcegraph) adapter — supports .cody/config.json and prompts."""

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


class CodyAdapter(AgentAdapter):
    name = "cody"
    display_name = "Cody (Sourcegraph)"

    def detect(self) -> bool:
        return (
            shutil.which("cody") is not None
            or Path.home().joinpath(".config", "cody").exists()
            or Path.home().joinpath(".vscode", "extensions").exists()
            and any(
                "sourcegraph" in p.name.lower()
                for p in Path.home().joinpath(".vscode", "extensions").iterdir()
                if p.is_dir()
            )
        )

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cody") / "config.json"
        return Path.home() / ".config" / "cody" / "config.json"

    def _prompts_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cody") / "prompts.md"
        return Path.home() / ".config" / "cody" / "prompts.md"

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cody") / "mcp_servers.json"
        return Path.home() / ".config" / "cody" / "mcp_servers.json"

    def backup(self) -> list[Path]:
        paths = [self._config_path("user"), self._prompts_path("user"), self._mcp_path("user")]
        backups = [backup_file(p) for p in paths if p.exists()]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user"), self._prompts_path("user"), self._mcp_path("user")]:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._mcp_path(scope)
        path.parent.mkdir(parents=True, exist_ok=True)
        config = read_json_safe(path)
        cody_mcp = config.get("cody.mcpServers")
        if not isinstance(cody_mcp, dict):
            cody_mcp = {}
            config["cody.mcpServers"] = cody_mcp
        cody_mcp["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. prompts.md
        path = self._prompts_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(path)

        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(path, new_content)

        return True
