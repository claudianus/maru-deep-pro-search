"""JetBrains AI adapter — supports .idea/ai-assistant.xml and project rules.

Official docs:
- https://www.jetbrains.com/help/ai-assistant/configure-project-rules.html
- https://www.jetbrains.com/help/ai-assistant/settings-reference-rules.html

JetBrains AI Assistant uses Markdown project rules that can be configured
via IDE settings. Rules support frontmatter with types:
- Always — applied to all chat sessions
- Manually — invoked via @rule: or #rule:
- By model decision — applied when model considers relevant
- By file patterns — applied when matching file patterns
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import (
    backup_file,
    read_text_safe,
    restore_file,
    write_text_safe,
)
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter


class JetBrainsAdapter(AgentAdapter):
    name = "jetbrains"
    display_name = "JetBrains AI"

    def detect(self) -> bool:
        home = Path.home()
        jetbrains_dirs = list(home.glob(".jetbrains*")) + list(
            home.glob("Library/Application Support/JetBrains*")
        )
        return bool(
            shutil.which("idea")
            or shutil.which("webstorm")
            or shutil.which("pycharm")
            or jetbrains_dirs
        )

    def _ai_assistant_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".idea") / "ai-assistant.xml"
        # JetBrains does not have a documented global AI assistant config file;
        # we use a marker in the home directory.
        return Path.home() / ".jetbrains-ai" / "maru-protocol.md"

    def _rules_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".idea") / "ai-assistant-rules"
        return Path.home() / ".jetbrains-ai" / "rules"

    def _skills_dir(self, scope: str) -> Path | None:
        return self._rules_dir(scope)

    skills_format = "flat"

    def backup(self) -> list[Path]:
        paths = [self._ai_assistant_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._ai_assistant_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        # JetBrains AI does not natively support MCP servers yet.
        return self.inject_rules(scope)

    def inject_rules(self, scope: str = "user") -> bool:
        protocol = get_protocol_for_agent(self.name)

        # 1. ai-assistant.xml / maru-protocol.md — legacy fallback
        path = self._ai_assistant_path(scope)
        content = read_text_safe(path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(path, new_content)

        # 2. .idea/ai-assistant-rules/*.md — JetBrains project rules format
        rules_dir = self._rules_dir(scope)
        rules_dir.mkdir(parents=True, exist_ok=True)

        rule_file = rules_dir / "maru-research-protocol.md"
        rule_content = read_text_safe(rule_file)
        new_rule = inject_protocol(rule_content, protocol)
        if new_rule != rule_content:
            write_text_safe(rule_file, new_rule)

        return True
