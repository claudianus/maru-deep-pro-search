"""Cline adapter — hooks, rules, agents, skills, cron, MCP.

Official docs:
- https://docs.cline.bot/customization/cline-rules        (Rules)
- https://docs.cline.bot/customization/hooks              (Hooks)
- https://docs.cline.bot/getting-started/config           (Config)

Extension surfaces:
1. .clinerules/*.md            — primary rules (project-level)
2. ~/Documents/Cline/Rules/*.md — global rules
3. .cline/hooks/PreToolUse.*   — lifecycle hooks (stdin JSON → stdout HOOK_CONTROL)
4. .cline/agents/*.md          — custom agents (YAML frontmatter)
5. .cline/skills/              — skills directory
6. .cline/cron/*.cron.md       — cron automation specs
7. ~/.cline/data/workflows/    — workflow definitions
8. CLINE_COMMAND_PERMISSIONS   — env var for shell restrictions
9. .cline/mcp.json             — MCP servers
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import backup_file, read_text_safe, restore_file, write_text_safe
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command

# ── Cline PreToolUse hook gate script ───────────────────────────────
_CLINE_PRETOOL_HOOK = '''#!/usr/bin/env python3
"""Cline PreToolUse hook — blocks edits/commands without research."""
import json
import os
import sys
import time

MARKER = os.path.expanduser("~/.maru/last_research")
TTL_SECONDS = 1800

def main() -> None:
    data = json.load(sys.stdin)
    hook_name = data.get("hookName", "")

    if hook_name != "PreToolUse":
        sys.exit(0)

    tool_data = data.get("preToolUse", {})
    tool_name = tool_data.get("toolName", "")

    # Only gate destructive tools
    if tool_name not in ("write_to_file", "apply_diff", "execute_command", "browser_action"):
        sys.exit(0)

    if not os.path.exists(MARKER):
        ctx = "[MARU] Research required before editing. Run deep_research first."
        print(f'HOOK_CONTROL{{"cancel":true,"contextModification":"{ctx}"}}')
        sys.exit(0)

    elapsed = time.time() - os.path.getmtime(MARKER)
    if elapsed > TTL_SECONDS:
        ctx = f"[MARU] Research expired ({elapsed/60:.0f}min). Re-run deep_research."
        print(f'HOOK_CONTROL{{"cancel":true,"contextModification":"{ctx}"}}')
        sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
'''

# ── Cline agent markdown ────────────────────────────────────────────
_CLINE_AGENT_MD = '''---
name: maru-research-gate
description: Enforces deep-research before any code generation or file edits
mode: primary
---
# Maru Research Gate Agent

You MUST call deep_research before any code generation, file edits, or architecture decisions.
This is enforced by the maru-deep-pro-search MCP server.
'''

# ── Cline cron spec ─────────────────────────────────────────────────
_CLINE_CRON_MD = '''---
name: maru-research-check
cronPattern: "0 */6 * * *"
providerId: openai
modelId: gpt-4o-mini
---
# Maru Research Check

Check if the project has had recent research activity. If not, remind the team
to run deep_research before making significant code changes.
'''


class ClineAdapter(AgentAdapter):
    name = "cline"
    display_name = "Cline"

    def detect(self) -> bool:
        return (
            Path.home().joinpath(".vscode", "extensions", "saoudrizwan.claude-dev").exists()
            or Path.home().joinpath(".vscode", "extensions", "claude-dev").exists()
            or shutil.which("cline") is not None
        )

    def _rules_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".clinerules")
        docs = Path.home() / "Documents"
        if not docs.exists():
            docs = Path.home()
        return docs / "Cline" / "Rules"

    def _hooks_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cline") / "hooks"
        return Path.home() / ".cline" / "hooks"

    def _agents_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cline") / "agents"
        return Path.home() / ".cline" / "agents"

    def _skills_dir(self, scope: str) -> Path | None:
        if scope == "project":
            return Path(".cline") / "skills"
        return Path.home() / ".cline" / "skills"

    skills_format = "flat"

    def _cron_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cline") / "cron"
        return Path.home() / ".cline" / "cron"

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cline", "mcp.json")
        return Path.home() / ".cline" / "mcp.json"

    def backup(self) -> list[Path]:
        paths = [
            self._mcp_path("user"),
            self._hooks_dir("user") / "PreToolUse.py",
        ]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._mcp_path("user"), self._hooks_dir("user") / "PreToolUse.py"]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        from ..backup import read_json_safe, write_json_safe

        path = self._mcp_path(scope)
        config = read_json_safe(path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        protocol = get_protocol_for_agent(self.name)

        # 1. .clinerules/*.md — primary rules
        rules_dir = self._rules_dir(scope)
        rules_dir.mkdir(parents=True, exist_ok=True)
        rule_file = rules_dir / "maru-research-protocol.md"
        content = read_text_safe(rule_file)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(rule_file, new_content)

        # 2. .cline/hooks/PreToolUse.py — lifecycle hook gate
        hooks_dir = self._hooks_dir(scope)
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_file = hooks_dir / "PreToolUse.py"
        if not hook_file.exists():
            hook_file.write_text(_CLINE_PRETOOL_HOOK, encoding="utf-8")
            hook_file.chmod(0o755)

        # 3. .cline/agents/*.md — custom agent
        agents_dir = self._agents_dir(scope)
        agents_dir.mkdir(parents=True, exist_ok=True)
        agent_file = agents_dir / "maru-research-gate.md"
        if not agent_file.exists():
            agent_file.write_text(_CLINE_AGENT_MD, encoding="utf-8")

        # 4. .cline/cron/*.cron.md — cron automation spec
        cron_dir = self._cron_dir(scope)
        cron_dir.mkdir(parents=True, exist_ok=True)
        cron_file = cron_dir / "maru-research-check.cron.md"
        if not cron_file.exists():
            cron_file.write_text(_CLINE_CRON_MD, encoding="utf-8")

        return True
