"""Windsurf adapter — Cascade Rules + Cascade Hooks + AGENTS.md + MCP.

Official docs:
- https://docs.windsurf.com/windsurf/cascade/hooks       (Cascade Hooks)
- https://docs.windsurf.com/windsurf/cascade/agents-md   (AGENTS.md)
- https://docs.windsurf.com/windsurf/cascade/memories-and-rules (Rules)

Extension surfaces:
1. .windsurf/rules/*.md        — official rules (flat markdown)
2. AGENTS.md                   — auto-discovered in project root/subdirs
3. .windsurf/hooks.json        — Cascade Hooks (pre_write_code, pre_mcp_tool_use, pre_user_prompt)
4. .codeium/windsurf/mcp_config.json — MCP servers
5. .codeiumignore              — ignore files
"""

from __future__ import annotations

import json
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
from .base import AgentAdapter, get_mcp_server_command

# ── Windsurf Cascade Hook gate script ───────────────────────────────
_WINDSURF_HOOK_SCRIPT = '''#!/usr/bin/env python3
"""Windsurf Cascade Hook — blocks edits/tool-calls without research."""
import json
import os
import sys
import time

MARKER = os.path.expanduser("~/.maru/last_research")
TTL_SECONDS = 1800  # 30 min

def main() -> None:
    data = json.load(sys.stdin)
    action = data.get("agent_action_name", "")

    # Only gate write-related and tool-use actions
    if action not in (
        "pre_write_code", "pre_mcp_tool_use", "pre_user_prompt"
    ):
        sys.exit(0)

    if not os.path.exists(MARKER):
        print("[MARU] Research required before editing. Run deep_research first.", file=sys.stderr)
        sys.exit(2)

    elapsed = time.time() - os.path.getmtime(MARKER)
    if elapsed > TTL_SECONDS:
        print(f"[MARU] Research expired ({elapsed/60:.0f}min). Re-run deep_research.", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
'''


class WindsurfAdapter(AgentAdapter):
    name = "windsurf"
    display_name = "Windsurf"

    def detect(self) -> bool:
        return (
            Path(".windsurf").exists()
            or Path.home().joinpath(".windsurf").exists()
            or shutil.which("windsurf") is not None
        )

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".codeium") / "windsurf" / "mcp_config.json"
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    def _hooks_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".windsurf") / "hooks.json"
        return Path.home() / ".codeium" / "windsurf" / "hooks.json"

    def _rules_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".windsurf") / "rules"
        return Path.home() / ".windsurf" / "rules"

    def _agents_md_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("AGENTS.md")
        return Path.home() / ".windsurf" / "AGENTS.md"

    def _skills_dir(self, scope: str) -> Path | None:
        if scope == "project":
            return Path(".windsurf") / "rules"
        return Path.home() / ".windsurf" / "rules"

    skills_format = "flat"

    def backup(self) -> list[Path]:
        paths = [
            self._mcp_path("user"),
            self._hooks_path("user"),
        ]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._mcp_path("user"), self._hooks_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        path = self._mcp_path(scope)
        config = read_json_safe(path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
        write_json_safe(path, config)
        return True

    def inject_rules(self, scope: str = "user") -> bool:
        protocol = get_protocol_for_agent(self.name)

        # 1. .windsurf/rules/*.md — official rule format
        rules_dir = self._rules_dir(scope)
        rules_dir.mkdir(parents=True, exist_ok=True)
        rule_file = rules_dir / "maru-research-protocol.md"
        rule_content = read_text_safe(rule_file)
        new_rule = inject_protocol(rule_content, protocol)
        if new_rule != rule_content:
            write_text_safe(rule_file, new_rule)

        # 2. AGENTS.md — auto-discovered by Windsurf Cascade
        agents_path = self._agents_md_path(scope)
        agents_content = read_text_safe(agents_path)
        new_agents = inject_protocol(agents_content, protocol)
        if new_agents != agents_content:
            write_text_safe(agents_path, new_agents)

        # 3. .windsurf/hooks.json — Cascade Hooks (3-layer gate)
        self._install_hooks(scope)

        return True

    def _install_hooks(self, scope: str) -> None:
        """Install Windsurf Cascade Hooks for research gating."""
        # Write the gate script to a known location
        gate_script = Path.home() / ".maru" / "windsurf_research_gate.py"
        gate_script.parent.mkdir(parents=True, exist_ok=True)
        if not gate_script.exists():
            gate_script.write_text(_WINDSURF_HOOK_SCRIPT, encoding="utf-8")
            gate_script.chmod(0o755)

        cmd = f"python3 {gate_script}"

        hooks_path = self._hooks_path(scope)
        hooks = read_json_safe(hooks_path)

        # Merge hook definitions (idempotent)
        hook_defs = {
            "pre_write_code": [{"command": cmd, "show_output": True}],
            "pre_mcp_tool_use": [{"command": cmd, "show_output": False}],
            "pre_user_prompt": [{"command": cmd, "show_output": False}],
        }

        for event, handlers in hook_defs.items():
            if event not in hooks:
                hooks[event] = []
            existing_cmds = [h.get("command", "") for h in hooks[event]]
            for h in handlers:
                if h["command"] not in existing_cmds:
                    hooks[event].append(h)

        write_json_safe(hooks_path, hooks)
