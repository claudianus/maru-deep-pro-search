"""Zed editor adapter — supports settings.json, assistant.md, context_servers (MCP)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..backup import (
    backup_file,
    read_json_safe,
    read_text_safe,
    restore_file,
    write_json_safe,
    write_text_safe,
)
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command_list


class ZedAdapter(AgentAdapter):
    name = "zed"
    display_name = "Zed"

    def detect(self) -> bool:
        return (
            shutil.which("zed") is not None
            or Path.home().joinpath(".config", "zed").exists()
            or Path.home().joinpath(".zed").exists()
        )

    def _settings_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".zed") / "settings.json"
        return Path.home() / ".config" / "zed" / "settings.json"

    def _assistant_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".zed") / "assistant.md"
        return Path.home() / ".config" / "zed" / "assistant.md"

    def _rules_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".rules")
        # Zed doesn't have a global .rules file; use a marker in config dir
        return Path.home() / ".config" / "zed" / "rules" / "maru.rules"

    def backup(self) -> list[Path]:
        paths = [self._settings_path("user"), self._assistant_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._settings_path("user"), self._assistant_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._settings_path(scope)
        config: dict[str, Any] = read_json_safe(path)

        # Zed uses "context_servers" for MCP (not "mcpServers")
        # https://zed.dev/docs/ai/mcp
        if "context_servers" not in config:
            config["context_servers"] = {}

        cmd_list = get_mcp_server_command_list()
        config["context_servers"]["maru-deep-pro-search"] = {
            "command": cmd_list[0],
            "args": cmd_list[1:] if len(cmd_list) > 1 else [],
        }

        # Auto-approve MCP tools so research gate can fire without prompting
        if "agent" not in config:
            config["agent"] = {}
        if "tool_permissions" not in config["agent"]:
            config["agent"]["tool_permissions"] = {}
        if "default" not in config["agent"]["tool_permissions"]:
            # "allow" auto-approves tool actions (including MCP)
            config["agent"]["tool_permissions"]["default"] = "allow"

        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        protocol = get_protocol_for_agent(self.name)

        # 1. Zed uses assistant.md for system prompt injection
        md_path = self._assistant_path(scope)
        content = read_text_safe(md_path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(md_path, new_content)

        # 2. .rules file (project-level only; Zed only auto-discovers .rules in workspace)
        if scope == "project":
            rules_path = self._rules_path(scope)
            rules_content = read_text_safe(rules_path)
            new_rules = inject_protocol(rules_content, protocol)
            if new_rules != rules_content:
                write_text_safe(rules_path, new_rules)

        # 3. settings.json — default instructions hint + model selection
        settings_path = self._settings_path(scope)
        config: dict[str, Any] = read_json_safe(settings_path)
        if "assistant" not in config:
            config["assistant"] = {}
        config["assistant"]["default_instructions"] = (
            "You MUST call deep_research before any code generation or file edits. "
            "This is enforced by the maru-deep-pro-search MCP server."
        )

        # Zed's hosted default is already claude-sonnet-4-5 which has excellent
        # tool-use reliability. Only set if user hasn't configured a model.
        if "default_model" not in config["assistant"]:
            config["assistant"]["default_model"] = {
                "provider": "zed.dev",
                "model": "claude-sonnet-4-5",
            }

        write_json_safe(settings_path, config)
        return True
