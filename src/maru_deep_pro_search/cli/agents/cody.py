"""Cody (Sourcegraph) adapter — supports .cody/config.json and prompts."""

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
from .base import AgentAdapter


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

    def backup(self) -> list[Path]:
        paths = [self._config_path("user"), self._prompts_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user"), self._prompts_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        # Cody does not natively support MCP servers yet.
        # We store the configuration in a marker file.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. prompts.md
        path = self._prompts_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(path)

        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(path, new_content)

        # 2. config.json — hint for future Cody versions
        config_path = self._config_path(scope)
        config = read_json_safe(config_path)
        if "instructions" not in config:
            config["instructions"] = {}
        config["instructions"]["research_first"] = (
            "You MUST call deep_research before any code generation or file edits. "
            "This is enforced by the maru-deep-pro-search MCP server."
        )
        write_json_safe(config_path, config)

        return True
