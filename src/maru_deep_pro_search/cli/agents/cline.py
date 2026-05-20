"""Cline adapter — hooks, rules, agents, skills, cron, MCP.

Official docs:
- https://docs.cline.bot/customization/cline-rules        (Rules)
- https://docs.cline.bot/customization/hooks              (Hooks)
- https://docs.cline.bot/getting-started/config           (Config)

Extension surfaces:
1. .clinerules/*.md            — primary rules (project-level)
2. ~/Documents/Cline/Rules/*.md — global rules
3. .cline/hooks/PreToolUse     — lifecycle hooks (stdin JSON → stdout JSON)
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

from ..backup import (
    backup_dir,
    backup_file,
    read_text_safe,
    restore_dir,
    restore_file,
    sorted_backup_paths,
    write_text_safe,
)
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_mcp_server_command

# ── Cline PreToolUse hook gate script ───────────────────────────────
_CLINE_PRETOOL_HOOK = '''#!/usr/bin/env python3
"""Cline PreToolUse hook — gates only freshness-sensitive search/network actions."""
import json
import os
import shlex
import sys
import time

MARKER = os.path.expanduser("~/.maru/last_research")
TTL_SECONDS = 1800
RESEARCH_TOOLS = {"browser_action", "WebSearch", "WebFetch", "search_web", "google_search", "brave_search"}
NETWORK_COMMANDS = {"curl", "wget", "http", "httpie", "lynx", "w3m", "links"}
PACKAGE_FRESHNESS = {
    ("npm", "view"), ("npm", "info"), ("pnpm", "view"), ("pnpm", "info"),
    ("yarn", "info"), ("pip", "index"), ("pip3", "index"),
}

def _words(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()

def _unwrap_command(command: str) -> str:
    words = _words(command)
    if len(words) >= 3 and words[0] == "lean-ctx" and words[1] == "-c":
        return words[2]
    if len(words) >= 3 and os.path.basename(words[0]) in {"bash", "sh", "zsh"} and words[1] in {"-c", "-lc"}:
        return words[2]
    return command

def _requires_research(tool_name: str, command: str) -> bool:
    if tool_name in RESEARCH_TOOLS:
        return True
    words = _words(_unwrap_command(command))
    if not words:
        return False
    executable = os.path.basename(words[0])
    second = words[1] if len(words) > 1 else ""
    return executable in NETWORK_COMMANDS or (executable, second) in PACKAGE_FRESHNESS

def main() -> None:
    data = json.load(sys.stdin)
    hook_name = data.get("hookName", "")

    if hook_name != "PreToolUse":
        sys.exit(0)

    tool_data = data.get("preToolUse", {})
    tool_name = tool_data.get("toolName", "")
    command = tool_data.get("command", "") or tool_data.get("input", {}).get("command", "")

    if not _requires_research(tool_name, command):
        sys.exit(0)

    if not os.path.exists(MARKER):
        msg = "[MARU] Research required for external freshness-sensitive action. Local edits and validation are allowed."
        print(json.dumps({"cancel": True, "errorMessage": msg}))
        sys.exit(0)

    elapsed = time.time() - os.path.getmtime(MARKER)
    if elapsed > TTL_SECONDS:
        msg = f"[MARU] Research expired ({elapsed/60:.0f}min). Re-run deep_research."
        print(json.dumps({"cancel": True, "errorMessage": msg}))
        sys.exit(0)

    print(json.dumps({"cancel": False}))
    sys.exit(0)

if __name__ == "__main__":
    main()
'''

# ── Cline agent markdown ────────────────────────────────────────────
_CLINE_AGENT_MD = """---
name: maru-research-gate
description: Enforces deep-research before any code generation or file edits
mode: primary
---
# Maru Research Gate Agent

You MUST call deep_research before any code generation, file edits, or architecture decisions.
This is enforced by the maru-deep-pro-search MCP server.
"""

# ── Cline cron spec ─────────────────────────────────────────────────
_CLINE_CRON_MD = """---
name: maru-research-check
cronPattern: "0 */6 * * *"
providerId: openai
modelId: gpt-4o-mini
---
# Maru Research Check

Check if the project has had recent research activity. If not, remind the team
to run deep_research before making significant code changes.
"""


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
        file_paths = [
            self._mcp_path("user"),
            self._hooks_dir("user") / "PreToolUse",
            self._hooks_dir("user") / "PreToolUse.py",
        ]
        dir_paths = [
            self._rules_dir("user"),
            self._agents_dir("user"),
            self._cron_dir("user"),
        ]
        skills = self._skills_dir("user")
        if skills is not None:
            dir_paths.append(skills)

        backups: list[Path] = []
        for p in file_paths:
            if p.exists():
                b = backup_file(p)
                if b is not None:
                    backups.append(b)
        for p in dir_paths:
            if p.exists():
                b = backup_dir(p)
                if b is not None:
                    backups.append(b)
        return backups

    def restore(self) -> bool:
        restored = False
        # Restore files
        for p in [
            self._mcp_path("user"),
            self._hooks_dir("user") / "PreToolUse",
            self._hooks_dir("user") / "PreToolUse.py",
        ]:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        # Restore directories
        dir_paths = [
            self._rules_dir("user"),
            self._agents_dir("user"),
            self._cron_dir("user"),
        ]
        skills = self._skills_dir("user")
        if skills is not None:
            dir_paths.append(skills)
        for p in dir_paths:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_dir(p, backups[0]) or restored
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

        hooks_dir = self._hooks_dir(scope)
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_file = hooks_dir / "PreToolUse"
        legacy_py = hooks_dir / "PreToolUse.py"
        if legacy_py.exists():
            legacy_py.unlink()
        existing_hook = read_text_safe(hook_file)
        should_write = (
            not hook_file.exists()
            or "MARU" in existing_hook
            or existing_hook.strip() == ""
            or existing_hook == _CLINE_PRETOOL_HOOK
        ) and existing_hook != _CLINE_PRETOOL_HOOK
        if should_write:
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
