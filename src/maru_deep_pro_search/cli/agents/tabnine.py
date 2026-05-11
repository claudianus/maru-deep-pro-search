"""Tabnine adapter — privacy-focused AI coding assistant."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .base import AgentAdapter
from ..backup import backup_file, read_text_safe, restore_file, write_text_safe
from ..prompts import get_protocol_for_agent


class TabnineAdapter(AgentAdapter):
    name = "tabnine"
    display_name = "Tabnine"

    def detect(self) -> bool:
        home = Path.home()
        vscode_ext = home / ".vscode" / "extensions"
        has_tabnine_ext = False
        if vscode_ext.exists():
            has_tabnine_ext = any(
                "tabnine" in p.name.lower()
                for p in vscode_ext.iterdir()
                if p.is_dir()
            )
        return (
            home.joinpath(".tabnine").exists()
            or has_tabnine_ext
        )

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".tabnine") / "config.json"
        return Path.home() / ".tabnine" / "config.json"

    def _prompts_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".tabnine") / "prompts.md"
        return Path.home() / ".tabnine" / "prompts.md"

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
        # Tabnine does not natively support MCP yet.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        path = self._prompts_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(path)

        if protocol not in content:
            header = "# maru-deep-pro-search Research Protocol\n\n"
            write_text_safe(path, content + "\n\n" + header + protocol + "\n")
        return True
