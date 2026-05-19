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

from ..backup import (
    backup_file,
    read_text_safe,
    restore_file,
    sorted_backup_paths,
    write_text_safe,
)
from ..prompts import (
    PROTOCOL_START_MARKER,
    get_protocol_for_agent,
    inject_protocol,
    text_has_research_protocol,
)
from ..toml_edit import (
    first_table_header_index,
    insert_root_block,
    key_at_root,
    remove_toml_key,
)
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
            backups = sorted_backup_paths(p)
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
        return remove_toml_key(lines, "developer_instructions")

    @staticmethod
    def _first_table_header_index(lines: list[str]) -> int:
        return first_table_header_index(lines)

    @staticmethod
    def _insert_root_block(lines: list[str], block: list[str]) -> list[str]:
        return insert_root_block(lines, block)

    @staticmethod
    def _build_developer_instructions_block(
        protocol: str, *, include_approval_policy: bool
    ) -> list[str]:
        block = ["", 'developer_instructions = """']
        block.extend(protocol.strip().splitlines())
        block.append('"""')
        if include_approval_policy:
            block.extend(
                [
                    "",
                    "# Auto-approve MCP tool calls from maru-deep-pro-search",
                    'approval_policy = "on-request"',
                ]
            )
        return block

    @staticmethod
    def _has_approval_policy_at_root(lines: list[str]) -> bool:
        return key_at_root(lines, "approval_policy")

    @staticmethod
    def _has_developer_instructions_key(lines: list[str]) -> bool:
        return any(line.strip().startswith("developer_instructions") for line in lines)

    @staticmethod
    def developer_instructions_at_root(lines: list[str]) -> bool:
        """True when ``developer_instructions`` sits before the first TOML table."""
        return key_at_root(lines, "developer_instructions")

    @staticmethod
    def has_nested_developer_instructions(lines: list[str]) -> bool:
        """True when ``developer_instructions`` was appended inside a TOML table."""
        return CodexAdapter._has_developer_instructions_key(
            lines
        ) and not CodexAdapter.developer_instructions_at_root(lines)

    @staticmethod
    def _should_manage_developer_instructions(content: str, lines: list[str]) -> bool:
        if CodexAdapter.has_nested_developer_instructions(lines):
            return True
        if not CodexAdapter._has_developer_instructions_key(lines):
            return True
        return text_has_research_protocol(content) or PROTOCOL_START_MARKER in content

    def inject_rules(self, scope: str = "user") -> bool:
        """Inject research protocol into Codex via three channels."""
        protocol = get_protocol_for_agent(self.name)

        # 1. AGENTS.md — Codex auto-discovers this in project root
        agents_path = self._agents_md_path(scope)
        content = read_text_safe(agents_path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(agents_path, new_content)

        config_path = self._config_path(scope)
        config_content = read_text_safe(config_path) or ""
        lines = config_content.splitlines() if config_content else []

        if self._should_manage_developer_instructions(config_content, lines):
            lines = self._remove_developer_instructions(lines)
            root_block = self._build_developer_instructions_block(
                protocol,
                include_approval_policy=not self._has_approval_policy_at_root(lines),
            )
            lines = self._insert_root_block(lines, root_block)
            write_text_safe(config_path, "\n".join(lines) + "\n")

        return True
