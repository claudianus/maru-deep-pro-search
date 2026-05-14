"""AntiGravity adapter."""

from __future__ import annotations

from pathlib import Path

from ..backup import backup_file, read_json_safe, restore_file, write_json_safe
from ..prompts import get_protocol_for_agent
from .base import AgentAdapter, get_mcp_server_command


class AntiGravityAdapter(AgentAdapter):
    name = "antigravity"
    display_name = "AntiGravity"

    def detect(self) -> bool:
        return Path.home().joinpath(".gemini", "antigravity").exists()

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".gemini") / "antigravity" / "mcp_config.json"
        return Path.home() / ".gemini" / "antigravity" / "mcp_config.json"

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".gemini") / "antigravity" / "config.json"
        return Path.home() / ".gemini" / "antigravity" / "config.json"

    def backup(self) -> list[Path]:
        path = self._mcp_path("user")
        b = backup_file(path)
        return [b] if b else []

    def restore(self) -> bool:
        path = self._mcp_path("user")
        backups = sorted(path.parent.glob(f"{path.name}.bak.*"), reverse=True)
        if backups:
            return restore_file(path, backups[0])
        return False

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._mcp_path(scope)
        config = read_json_safe(path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        # AntiGravity has limited programmatic rule injection.
        # We inject a comment/header in the mcp_config.json as a fallback,
        # and print a manual instruction for the user.
        path = self._mcp_path(scope)
        config = read_json_safe(path)
        protocol = get_protocol_for_agent(self.name)

        # Store protocol in a custom key that won't break MCP
        config.setdefault("_maru_deep_pro_search_notes", {})
        config["_maru_deep_pro_search_notes"]["research_protocol"] = protocol
        write_json_safe(path, config)

        # Also store in a separate config file for future AntiGravity versions
        config_path = self._config_path(scope)
        ag_config = read_json_safe(config_path)
        if "instructions" not in ag_config:
            ag_config["instructions"] = {}
        ag_config["instructions"]["research_first"] = (
            "You MUST call deep_research before any code generation or file edits. "
            "This is enforced by the maru-deep-pro-search MCP server."
        )
        write_json_safe(config_path, ag_config)

        # AntiGravity doesn't have a direct system prompt file we can edit.
        # Return False to signal that manual steps may be needed.
        return False
