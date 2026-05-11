"""Devin (Cognition AI) adapter — supports Devin workspace rules."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .base import AgentAdapter
from ..backup import backup_file, read_text_safe, restore_file, write_text_safe
from ..prompts import get_protocol_for_agent


class DevinAdapter(AgentAdapter):
    name = "devin"
    display_name = "Devin"

    def detect(self) -> bool:
        return (
            shutil.which("devin") is not None
            or Path.home().joinpath(".devin").exists()
            or Path(".devin").exists()
        )

    def _rules_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".devin") / "rules.md"
        return Path.home() / ".devin" / "rules.md"

    def backup(self) -> list[Path]:
        paths = [self._rules_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._rules_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        # Devin does not natively support MCP yet.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        path = self._rules_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(path)

        if protocol not in content:
            header = "# maru-deep-pro-search Research Protocol\n\n"
            write_text_safe(path, content + "\n\n" + header + protocol + "\n")
        return True
