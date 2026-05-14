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
    write_json_safe,
    write_text_safe,
)
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter


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

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".amazonq") / "config.json"
        return Path.home() / ".amazonq" / "config.json"

    def backup(self) -> list[Path]:
        paths = [self._config_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        # Amazon Q does not natively support MCP yet.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        # 1. .amazonq/rules/*.md — official Amazon Q format
        rules_dir = self._rules_dir(scope)
        rules_dir.mkdir(parents=True, exist_ok=True)

        rule_file = rules_dir / "maru-research-protocol.md"
        protocol = get_protocol_for_agent(self.name)

        content = read_text_safe(rule_file)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(rule_file, new_content)

        # 2. config.json — hint for future Amazon Q versions
        config_path = self._config_path(scope)
        config = read_json_safe(config_path)
        if "instructions" not in config:
            config["instructions"] = {}
        config["instructions"]["research_first"] = (
            "You MUST call deep_research before any code generation or file edits. "
            "This is enforced by the maru-deep-pro-search MCP server."
        )
        write_json_safe(config_path, config)

        return True
