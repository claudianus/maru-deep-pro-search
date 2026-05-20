"""Amazon Q Developer adapter — AWS IDE integrations.

Official docs: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/context-project-rules.html

Amazon Q Developer uses Markdown project rules stored in:
- Project:  .amazonq/rules/*.md
Amazon Q automatically discovers and applies these rules as context.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import (
    backup_file,
    read_json_safe,
    read_text_safe,
    restore_file,
    sorted_backup_paths,
    write_json_safe,
    write_text_safe,
)
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command


class AmazonQAdapter(AgentAdapter):
    name = "amazon_q"
    display_name = "Amazon Q Developer"

    def detect(self) -> bool:
        return (
            shutil.which("q") is not None
            or Path.home().joinpath(".aws", "amazonq").exists()
            or (
                Path.home().joinpath(".vscode", "extensions").exists()
                and any(
                    p.name.startswith("amazon-q")
                    for p in Path.home().joinpath(".vscode", "extensions").iterdir()
                    if p.is_dir()
                )
            )
        )

    def _rules_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".amazonq") / "rules"
        return Path.home() / ".amazonq" / "rules"

    def _skills_dir(self, scope: str) -> Path | None:
        return self._rules_dir(scope)

    skills_format = "flat"

    def _rule_file(self, scope: str) -> Path:
        return self._rules_dir(scope) / "maru-research-protocol.md"

    def _mcp_paths(self, scope: str) -> list[Path]:
        if scope == "project":
            return [
                Path(".amazonq") / "mcp.json",
                Path(".amazonq") / "default.json",
            ]
        return [
            Path.home() / ".aws" / "amazonq" / "mcp.json",
            Path.home() / ".aws" / "amazonq" / "default.json",
        ]

    def backup(self) -> list[Path]:
        paths = [self._rule_file("user")] + self._mcp_paths("user")
        backups = [backup_file(p) for p in paths if p.exists()]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        paths = [self._rule_file("user")] + self._mcp_paths("user")
        for p in paths:
            backs = sorted_backup_paths(p)
            if backs:
                restored = restore_file(p, backs[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        paths = self._mcp_paths(scope)
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            config = read_json_safe(path)
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
            write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. .amazonq/rules/*.md — official Amazon Q format
        rules_dir = self._rules_dir(scope)
        rules_dir.mkdir(parents=True, exist_ok=True)

        rule_file = self._rule_file(scope)
        protocol = get_protocol_for_agent(self.name)

        content = read_text_safe(rule_file)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(rule_file, new_content)

        return True
