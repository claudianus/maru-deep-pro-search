"""JetBrains AI adapter — supports .idea/ai-assistant.xml and prompts."""

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


class JetBrainsAdapter(AgentAdapter):
    name = "jetbrains"
    display_name = "JetBrains AI"

    def detect(self) -> bool:
        # Look for JetBrains Toolbox or any IDE config directory
        home = Path.home()
        jetbrains_dirs = list(home.glob(".jetbrains*")) + list(
            home.glob("Library/Application Support/JetBrains*")
        )
        return bool(
            shutil.which("idea")
            or shutil.which("webstorm")
            or shutil.which("pycharm")
            or jetbrains_dirs
        )

    def _ai_assistant_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".idea") / "ai-assistant.xml"
        # JetBrains does not have a global AI assistant config file;
        # we use a marker in the home directory.
        return Path.home() / ".jetbrains-ai" / "maru-protocol.md"

    def _settings_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".idea") / "maru-settings.json"
        return Path.home() / ".jetbrains-ai" / "maru-settings.json"

    def backup(self) -> list[Path]:
        paths = [self._ai_assistant_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._ai_assistant_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        # JetBrains AI does not natively support MCP servers yet.
        # We inject rules via the ai-assistant.xml or markdown file.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. ai-assistant.xml / maru-protocol.md
        path = self._ai_assistant_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(path)

        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(path, new_content)

        # 2. maru-settings.json — hint for future JetBrains AI versions
        settings_path = self._settings_path(scope)
        settings = read_json_safe(settings_path)
        if "instructions" not in settings:
            settings["instructions"] = {}
        settings["instructions"]["research_first"] = (
            "You MUST call deep_research before any code generation or file edits. "
            "This is enforced by the maru-deep-pro-search MCP server."
        )
        write_json_safe(settings_path, settings)

        return True
