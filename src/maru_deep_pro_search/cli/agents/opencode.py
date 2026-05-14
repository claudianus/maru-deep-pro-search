"""OpenCode adapter.

Official docs: https://opencode.ai/docs/agents

OpenCode supports agents via:
- JSON config in opencode.json (agents section)
- Markdown files in ~/.config/opencode/agents/ or .opencode/agents/
- The markdown filename becomes the agent name.
"""

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
from .base import AgentAdapter, get_mcp_server_command_list


class OpenCodeAdapter(AgentAdapter):
    name = "opencode"
    display_name = "OpenCode"

    def detect(self) -> bool:
        return (
            shutil.which("opencode") is not None
            or Path.home().joinpath(".config", "opencode").exists()
        )

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("opencode.json")
        return Path.home() / ".config" / "opencode" / "opencode.json"

    def _agents_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".opencode") / "agents"
        return Path.home() / ".config" / "opencode" / "agents"

    def _agents_md_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("AGENTS.md")
        return Path.home() / ".config" / "opencode" / "AGENTS.md"

    def backup(self) -> list[Path]:
        paths = [self._config_path("user"), self._agents_md_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user"), self._agents_md_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

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
        protocol = get_protocol_for_agent(self.name)

        # 1. AGENTS.md — auto-discovered by OpenCode
        agents_md_path = self._agents_md_path(scope)
        content = read_text_safe(agents_md_path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(agents_md_path, new_content)

        # 2. .opencode/agents/*.md — official OpenCode agent format
        agents_dir = self._agents_dir(scope)
        agents_dir.mkdir(parents=True, exist_ok=True)

        agent_file = agents_dir / "maru-research-gate.md"
        agent_content = read_text_safe(agent_file)
        new_agent = inject_protocol(agent_content, protocol)
        if new_agent != agent_content:
            write_text_safe(agent_file, new_agent)

        # 3. opencode.json — register the agent in config
        config_path = self._config_path(scope)
        config = read_json_safe(config_path)

        if "agents" not in config:
            config["agents"] = {}
        if "maru-research-gate" not in config["agents"]:
            config["agents"]["maru-research-gate"] = {
                "description": "Enforces deep-research before any code generation",
                "mode": "primary",
                "prompt": str(
                    self._agents_dir(scope).relative_to(
                        Path(".") if scope == "project" else Path.home()
                    )
                    / "maru-research-gate.md"
                ),
            }

        write_json_safe(config_path, config)
        return True
