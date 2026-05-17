"""Abstract base class for agent adapters."""

from __future__ import annotations

import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import maru_deep_pro_search


def get_mcp_server_command() -> dict[str, Any]:
    """Return the MCP server command configuration for JSON-based agents.

    Tries to find the installed ``maru-deep-pro-search`` binary first.
    Falls back to ``sys.executable`` with the module path.
    """
    binary = shutil.which("maru-deep-pro-search")
    if binary:
        return {"command": binary, "args": []}
    return {"command": sys.executable, "args": ["-m", "maru_deep_pro_search.server"]}


def get_continue_experimental_mcp_entry() -> dict[str, Any]:
    """JSON entry for Continue ``experimental.modelContextProtocolServers`` (stdio).

    See: https://docs.continue.dev/reference/yaml-migration
    """
    spec = get_mcp_server_command()
    return {
        "transport": {
            "type": "stdio",
            "command": spec["command"],
            "args": list(spec.get("args") or []),
            "env": dict(spec.get("env") or {}),
        }
    }


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
    skills_format: str = "flat"  # "flat" (cursor, continue) or "nested" (kimi, claude, cline)

    @abstractmethod
    def detect(self) -> bool:
        """Return True if this agent is installed on the system."""
        ...

    @abstractmethod
    def install_mcp(self, scope: str = "user") -> bool:
        """Register maru-deep-pro-search MCP server in agent config.

        Args:
            scope: ``"user"`` (global, default for ``setup`` / ``sync``) or ``"project"``
                (legacy; not used by the official CLI — avoid writing agent files in repos).

        Returns:
            True on success
        """
        ...

    @abstractmethod
    def inject_rules(self, scope: str = "user") -> bool:
        """Inject the research-first protocol into agent rules/settings.

        Args:
            scope: ``"user"`` (global, default for ``setup`` / ``sync``) or ``"project"``
                (legacy; not used by the official CLI — avoid writing agent files in repos).

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

    def _skills_dir(self, scope: str) -> Path | None:
        """Return the agent-specific directory for skill files.

        Override in subclasses that support skill files (e.g. Cursor).
        """
        return None

    def _get_skills_source_dir(self) -> Path:
        """Return the directory containing packaged SKILL.md files."""
        return Path(maru_deep_pro_search.__file__).parent / "skills"

    def install_skills(self, scope: str = "user") -> bool:
        """Copy SKILL.md files to the agent's rules directory."""
        source = self._get_skills_source_dir()
        target = self._skills_dir(scope)
        if target is None:
            return False
        if not source.exists():
            return False

        target.mkdir(parents=True, exist_ok=True)
        copied = 0
        for skill_dir in source.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    if self.skills_format == "nested":
                        dest_dir = target / skill_dir.name
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest = dest_dir / "SKILL.md"
                    else:
                        dest = target / f"{skill_dir.name}.md"
                    shutil.copy2(skill_file, dest)
                    copied += 1
        return copied > 0

    def verify_setup(self, scope: str = "user") -> dict[str, bool]:
        """Read-only status check. Override in subclasses when needed."""
        from ..verify_status import verify_adapter

        return verify_adapter(self, scope)

    def refresh_managed_hooks(self, *, repair: bool = False) -> bool:
        """Overwrite maru-managed hook scripts when *repair* is True. Override in adapters."""
        _ = repair
        return True

    def _inject_rules_with_repair(self, scope: str, *, repair: bool) -> bool:
        try:
            return self.inject_rules(scope, repair=repair)  # type: ignore[call-arg]
        except TypeError:
            return self.inject_rules(scope)

    def configure(
        self,
        scope: str = "user",
        *,
        repair: bool = False,
        repair_skills: bool = False,
    ) -> dict[str, Any]:
        """Full setup: backup → install MCP → inject rules → install skills."""
        backups = self.backup()
        mcp_ok = self.install_mcp(scope)
        if repair:
            self.refresh_managed_hooks(repair=True)
        rules_ok = self._inject_rules_with_repair(scope, repair=repair)
        skills_dir = self._skills_dir(scope)
        if skills_dir is None or (repair and not repair_skills):
            skills_ok = None
        else:
            skills_ok = self.install_skills(scope)
        return {
            "backups": [str(b) for b in backups if b],
            "mcp_installed": mcp_ok,
            "rules_injected": rules_ok,
            "skills_installed": skills_ok,
            "skills_supported": skills_dir is not None,
            "success": mcp_ok and rules_ok,
        }
