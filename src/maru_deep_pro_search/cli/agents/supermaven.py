"""Supermaven adapter — supports .supermaven/config.json."""

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


class SupermavenAdapter(AgentAdapter):
    name = "supermaven"
    display_name = "Supermaven"

    def detect(self) -> bool:
        return (
            shutil.which("supermaven") is not None or Path.home().joinpath(".supermaven").exists()
        )

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".supermaven") / "config.json"
        return Path.home() / ".supermaven" / "config.json"

    def _rules_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".supermaven") / "rules.md"
        return Path.home() / ".supermaven" / "rules.md"

    def backup(self) -> list[Path]:
        paths = [self._config_path("user"), self._rules_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user"), self._rules_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        # Supermaven does not support MCP natively yet.
        # We store the protocol as rules.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. rules.md
        path = self._rules_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(path)

        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(path, new_content)

        # 2. config.json — hint for future Supermaven versions
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
