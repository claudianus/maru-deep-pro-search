"""Kilo Code adapter."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import backup_file, read_json_safe, restore_file, write_json_safe
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command_list


class KiloAdapter(AgentAdapter):
    name = "kilo"
    display_name = "Kilo Code"

    def detect(self) -> bool:
        return Path.home().joinpath(".config", "kilo").exists() or shutil.which("kilo") is not None

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("kilo.jsonc")
        return Path.home() / ".config" / "kilo" / "kilo.jsonc"

    def _skills_dir(self, scope: str) -> Path | None:
        if scope == "project":
            return Path(".kilo") / "rules"
        return Path.home() / ".config" / "kilo" / "rules"

    skills_format = "flat"

    def backup(self) -> list[Path]:
        path = self._config_path("user")
        b = backup_file(path)
        return [b] if b else []

    def restore(self) -> bool:
        path = self._config_path("user")
        backups = sorted(path.parent.glob(f"{path.name}.bak.*"), reverse=True)
        if backups:
            return restore_file(path, backups[0])
        return False

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._config_path(scope)
        config = read_json_safe(path)
        if "mcp" not in config:
            config["mcp"] = {}

        config["mcp"]["maru-deep-pro-search"] = {
            "type": "local",
            "command": get_mcp_server_command_list(),
            "enabled": True,
        }
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        path = self._config_path(scope)
        config = read_json_safe(path)

        protocol = get_protocol_for_agent(self.name)
        current = config.get("systemPrompt", "")
        new_prompt = inject_protocol(current, protocol)
        if new_prompt != current:
            config["systemPrompt"] = new_prompt

        # Ensure .kilo/rules/*.md is referenced in instructions
        if "instructions" not in config:
            config["instructions"] = []
        rules_glob = ".kilo/rules/*.md" if scope == "project" else (
            str(Path.home() / ".config" / "kilo" / "rules" / "*.md")
        )
        if rules_glob not in config["instructions"]:
            config["instructions"].append(rules_glob)

        # Experimental features for better research integration
        if "experimental" not in config:
            config["experimental"] = {}
        config["experimental"]["codebase_search"] = True

        if "auto_collapse_reasoning" not in config:
            config["auto_collapse_reasoning"] = True

        write_json_safe(path, config)
        return True
