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
        return shutil.which("codex") is not None or Path.home().joinpath(".codex").exists()

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

    @staticmethod
    def _has_mcp_server(content: str) -> bool:
        return "[mcp_servers.maru-deep-pro-search]" in content

    @staticmethod
    def _has_codex_hooks(content: str) -> bool:
        """Check if codex_hooks is already enabled in any [features] section."""
        lines = content.splitlines()
        in_features = False
        for line in lines:
            stripped = line.strip()
            if stripped == "[features]":
                in_features = True
                continue
            if in_features:
                if stripped.startswith("["):
                    break  # next section
                if stripped.startswith("codex_hooks"):
                    return True
        return False

    @staticmethod
    def _insert_or_update_features(lines: list[str]) -> list[str]:
        """Ensure [features] section exists with codex_hooks = true.

        Idempotent: will not duplicate [features] or codex_hooks.
        """
        # First, check if codex_hooks already exists anywhere in [features]
        if CodexAdapter._has_codex_hooks("\n".join(lines)):
            return lines

        # Find [features] section and insert codex_hooks inside it
        features_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "[features]":
                features_idx = i
                break

        if features_idx is not None:
            # Insert after [features] line, before next section or EOF
            insert_pos = features_idx + 1
            for j in range(features_idx + 1, len(lines)):
                if lines[j].strip().startswith("["):
                    insert_pos = j
                    break
                else:
                    insert_pos = j + 1
            lines.insert(insert_pos, "codex_hooks = true")
            return lines

        # No [features] section — append at end
        lines.append("")
        lines.append("[features]")
        lines.append("codex_hooks = true")
        return lines

    def install_mcp(self, scope: str = "user") -> bool:
        """Register maru MCP in ~/.codex/config.toml."""
        path = self._config_path(scope)
        content = read_text_safe(path) or ""
        lines = content.splitlines() if content else []

        # Build MCP server block
        cmd_list = get_mcp_server_command_list()
        cmd = cmd_list[0]
        args = cmd_list[1:] if len(cmd_list) > 1 else []

        if not self._has_mcp_server(content):
            mcp_block = f'[mcp_servers.maru-deep-pro-search]\ncommand = "{cmd}"\n'
            if args:
                args_toml = ", ".join(f'"{a}"' for a in args)
                mcp_block += f"args = [{args_toml}]\n"
            mcp_block += "enabled = true\n"
            lines.append("")
            lines.append(mcp_block.rstrip())

        lines = self._insert_or_update_features(lines)
        write_text_safe(path, "\n".join(lines) + "\n")
        return True

    @staticmethod
    def _remove_developer_instructions(lines: list[str]) -> list[str]:
        """Remove developer_instructions key (including multiline strings) from TOML lines."""
        # Handles:
        # - developer_instructions = """..."""
        # - developer_instructions = "..."
        # - developer_instructions = '''...'''
        result: list[str] = []
        state = "normal"  # normal | in_ml_double | in_ml_single
        for line in lines:
            stripped = line.strip()
            if state == "normal":
                if stripped.startswith("developer_instructions"):
                    # Check if multiline starts on same line
                    rest = stripped.split("=", 1)[1].strip() if "=" in stripped else ""
                    if rest.startswith('"""'):
                        if rest.endswith('"""') and len(rest) > 3:
                            # Single-line multiline — skip entirely
                            continue
                        state = "in_ml_double"
                        continue
                    elif rest.startswith("'''"):
                        if rest.endswith("'''") and len(rest) > 3:
                            continue
                        state = "in_ml_single"
                        continue
                    else:
                        # Single-line non-multiline — skip
                        continue
                result.append(line)
            elif state == "in_ml_double":
                if stripped.endswith('"""'):
                    state = "normal"
                continue
            elif state == "in_ml_single":
                if stripped.endswith("'''"):
                    state = "normal"
                continue
        return result

    @staticmethod
    def _has_approval_policy(lines: list[str]) -> bool:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("approval_policy"):
                return True
        return False

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

        # Remove old developer_instructions completely (including multiline)
        lines = self._remove_developer_instructions(lines)

        # Append new developer_instructions (TOML multiline string)
        lines.append("")
        lines.append('developer_instructions = """')
        for rule_line in protocol.strip().splitlines():
            lines.append(rule_line)
        lines.append('"""')

        # 3. Approval policy — set granular approvals so research gate works
        if not self._has_approval_policy(lines):
            lines.append("")
            lines.append("# Auto-approve MCP tool calls from maru-deep-pro-search")
            lines.append('approval_policy = "on-request"')

        write_text_safe(config_path, "\n".join(lines) + "\n")
        return True
