"""Codeium adapter — supports .codeium/config.json and system prompts."""

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


class CodeiumAdapter(AgentAdapter):
    name = "codeium"
    display_name = "Codeium"

    def detect(self) -> bool:
        return (
            shutil.which("codeium") is not None
            or Path.home().joinpath(".codeium").exists()
            or Path.home().joinpath(".vscode", "extensions").exists()
            and any(
                "codeium" in p.name.lower()
                for p in Path.home().joinpath(".vscode", "extensions").iterdir()
                if p.is_dir()
            )
        )

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".codeium") / "config.json"
        return Path.home() / ".codeium" / "config.json"

    def _prompts_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".codeium") / "system-prompt.md"
        return Path.home() / ".codeium" / "system-prompt.md"

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
        # Codeium does not natively support MCP servers yet.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. system-prompt.md
        path = self._prompts_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(path)

        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(path, new_content)

        # 2. config.json — hint for future Codeium versions
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
