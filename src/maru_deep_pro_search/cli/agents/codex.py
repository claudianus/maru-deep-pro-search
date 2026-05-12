"""OpenAI Codex adapter — terminal-based AI coding agent.

Codex uses TOML config (~/.codex/config.toml) with:
- [mcp_servers.<id>] for MCP registration
- developer_instructions for session-level rules
- features.codex_hooks to enable lifecycle hooks
- AGENTS.md for project-level rules (auto-discovered)
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import backup_file, read_text_safe, restore_file, write_text_safe
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command_list


class CodexAdapter(AgentAdapter):
    name = "codex"
    display_name = "OpenAI Codex"

    def detect(self) -> bool:
        return (
            shutil.which("codex") is not None
            or Path.home().joinpath(".codex").exists()
        )

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".codex") / "config.toml"
        return Path.home() / ".codex" / "config.toml"

    def _agents_md_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("AGENTS.md")
        return Path.home() / ".codex" / "AGENTS.md"

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
        """Register maru MCP in ~/.codex/config.toml."""
        path = self._config_path(scope)
        content = read_text_safe(path) or ""

        # Parse existing TOML naïvely (line-based)
        lines = content.splitlines() if content else []

        # Build MCP server block
        cmd_list = get_mcp_server_command_list()
        cmd = cmd_list[0]
        args = cmd_list[1:] if len(cmd_list) > 1 else []

        mcp_block = f'[mcp_servers.maru-deep-pro-search]\ncommand = "{cmd}"\n'
        if args:
            args_toml = ', '.join(f'"{a}"' for a in args)
            mcp_block += f"args = [{args_toml}]\n"
        mcp_block += 'enabled = true\n'

        # Check if already present
        if "[mcp_servers.maru-deep-pro-search]" not in content:
            lines.append("")
            lines.append(mcp_block.rstrip())

        # Enable hooks feature (needed for lifecycle hooks)
        if "features.codex_hooks" not in content:
            lines.append("")
            lines.append("[features]")
            lines.append("codex_hooks = true")

        write_text_safe(path, "\n".join(lines) + "\n")
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        """Inject research protocol into Codex via three channels."""
        protocol = get_protocol_for_agent(self.name)

        # 1. AGENTS.md — Codex auto-discovers this in project root
        agents_path = self._agents_md_path(scope)
        content = read_text_safe(agents_path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(agents_path, new_content)

        # 2. ~/.codex/config.toml — developer_instructions
        config_path = self._config_path(scope)
        config_content = read_text_safe(config_path) or ""
        lines = config_content.splitlines() if config_content else []

        # Remove old developer_instructions if present
        filtered: list[str] = []
        skip = False
        for line in lines:
            if line.strip().startswith("developer_instructions"):
                skip = True
                continue
            if skip and line.startswith(" "):
                continue
            skip = False
            filtered.append(line)

        # Append new developer_instructions (TOML multiline string)
        filtered.append("")
        filtered.append('developer_instructions = """')
        for rule_line in protocol.strip().splitlines():
            filtered.append(rule_line)
        filtered.append('"""')

        write_text_safe(config_path, "\n".join(filtered) + "\n")

        # 3. Approval policy — set granular approvals so research gate works
        if "approval_policy" not in config_content:
            filtered2 = read_text_safe(config_path).splitlines()
            filtered2.append("")
            filtered2.append("# Auto-approve MCP tool calls from maru-deep-pro-search")
            filtered2.append('approval_policy = "on-request"')
            write_text_safe(config_path, "\n".join(filtered2) + "\n")

        return True
