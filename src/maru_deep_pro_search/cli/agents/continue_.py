"""Continue adapter — open-source AI coding assistant for VS Code / JetBrains."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import backup_file, read_json_safe, restore_file, write_json_safe
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command


class ContinueAdapter(AgentAdapter):
    name = "continue"
    display_name = "Continue"

    def detect(self) -> bool:
        return (
            shutil.which("continue") is not None
            or Path.home().joinpath(".continue", "config.json").exists()
            or Path.home().joinpath(".config", "continue", "config.json").exists()
        )

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".continue", "config.json")
        # Continue uses ~/.continue/config.json on all platforms
        return Path.home() / ".continue" / "config.json"

    def _ignore_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".continueignore")
        return Path.home() / ".continueignore"

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
        # Continue supports MCP via config.json "server" section
        path = self._config_path(scope)
        config = read_json_safe(path)
        if "server" not in config:
            config["server"] = {}
        if "mcpServers" not in config["server"]:
            config["server"]["mcpServers"] = {}

        config["server"]["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        # Continue uses custom system message / prompts in config.json
        path = self._config_path(scope)
        config = read_json_safe(path)
        protocol = get_protocol_for_agent(self.name)

        if "custom_commands" not in config:
            config["custom_commands"] = []

        # Add /research and /verify commands if not exists
        existing_names = [c.get("name", "") for c in config["custom_commands"]]
        if "research" not in existing_names:
            config["custom_commands"].append(
                {
                    "name": "research",
                    "description": "Run deep research before any code change",
                    "prompt": (
                        "Before writing or modifying any code, call deep_research "
                        "with the user's request as the query. Summarize findings and "
                        "wait for confirmation before proceeding."
                    ),
                }
            )
        if "verify" not in existing_names:
            config["custom_commands"].append(
                {
                    "name": "verify",
                    "description": "Verify research was completed for this session",
                    "prompt": (
                        "Check if deep_research has been called in this session. "
                        "If not, refuse to proceed and instruct the user to run /research first."
                    ),
                }
            )

        # Inject system message
        current = config.get("system_message", "")
        new_prompt = inject_protocol(current, protocol)
        if new_prompt != current:
            config["system_message"] = new_prompt

        write_json_safe(path, config)

        # .continueignore for harness artifacts
        ignore_path = self._ignore_path(scope)
        if not ignore_path.exists():
            ignore_path.write_text(
                ".maru/knowledge.db\n.maru/knowledge.db-journal\n", encoding="utf-8"
            )

        return True
