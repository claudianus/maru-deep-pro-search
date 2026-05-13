"""Abstract base class for agent adapters."""

from __future__ import annotations

import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


def get_mcp_server_command() -> dict[str, Any]:
    """Return the MCP server command configuration for JSON-based agents.

    Tries to find the installed ``maru-deep-pro-search`` binary first.
    Falls back to ``sys.executable`` with the module path.
    """
    binary = shutil.which("maru-deep-pro-search")
    if binary:
        return {"command": binary, "args": []}
    return {"command": sys.executable, "args": ["-m", "maru_deep_pro_search.server"]}


def get_mcp_server_command_list() -> list[str]:
    """Return the MCP server command as a list for agents using list format."""
    binary = shutil.which("maru-deep-pro-search")
    if binary:
        return [binary]
    return [sys.executable, "-m", "maru_deep_pro_search.server"]


def get_mcp_server_yaml() -> str:
    """Return the MCP server YAML block for Hermes-style configs."""
    binary = shutil.which("maru-deep-pro-search")
    if binary:
        return f"  maru-deep-pro-search:\n    command: {binary}\n    args: []\n"
    return (
        f"  maru-deep-pro-search:\n"
        f"    command: {sys.executable}\n"
        f"    args:\n"
        f"      - -m\n"
        f"      - maru_deep_pro_search.server\n"
    )


class AgentAdapter(ABC):
    """Adapter for configuring a specific AI agent."""

    name: str = ""
    display_name: str = ""

    @abstractmethod
    def detect(self) -> bool:
        """Return True if this agent is installed on the system."""
        ...

    @abstractmethod
    def install_mcp(self, scope: str = "user") -> bool:
        """Register maru-deep-pro-search MCP server in agent config.

        Args:
            scope: "user" or "project"

        Returns:
            True on success
        """
        ...

    @abstractmethod
    def inject_rules(self, scope: str = "user") -> bool:
        """Inject the research-first protocol into agent rules/settings.

        Args:
            scope: "user" or "project"

        Returns:
            True on success
        """
        ...

    @abstractmethod
    def backup(self) -> list[Path]:
        """Backup current agent configs. Returns list of backup paths."""
        ...

    @abstractmethod
    def restore(self) -> bool:
        """Restore agent configs from the most recent backup."""
        ...

    def configure(self, scope: str = "user") -> dict[str, Any]:
        """Full setup: backup → install MCP → inject rules."""
        backups = self.backup()
        mcp_ok = self.install_mcp(scope)
        rules_ok = self.inject_rules(scope)
        return {
            "backups": [str(b) for b in backups if b],
            "mcp_installed": mcp_ok,
            "rules_injected": rules_ok,
            "success": mcp_ok and rules_ok,
        }
