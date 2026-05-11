"""Claude Code adapter — supports .claude/settings.json, CLAUDE.md, commands/, hooks."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

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


class ClaudeAdapter(AgentAdapter):
    name = "claude"
    display_name = "Claude Code"

    # ── detect ──────────────────────────────────────────────────
    def detect(self) -> bool:
        return (
            shutil.which("claude") is not None
            or Path.home().joinpath(".claude").exists()
        )

    # ── paths (2025 layout) ─────────────────────────────────────
    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".mcp.json")
        return Path.home() / ".claude" / ".mcp.json"

    def _settings_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".claude") / "settings.json"
        return Path.home() / ".claude" / "settings.json"

    def _claude_md_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("CLAUDE.md")
        return Path.home() / ".claude" / "CLAUDE.md"

    def _commands_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".claude") / "commands"
        return Path.home() / ".claude" / "commands"

    # ── backup ──────────────────────────────────────────────────
    def backup(self) -> list[Path]:
        paths = [
            self._mcp_path("user"),
            self._settings_path("user"),
            self._claude_md_path("user"),
        ]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [
            self._mcp_path("user"),
            self._settings_path("user"),
            self._claude_md_path("user"),
        ]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    # ── install MCP ─────────────────────────────────────────────
    def install_mcp(self, scope: str = "user") -> bool:
        path = self._mcp_path(scope)
        config = read_json_safe(path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["maru-deep-pro-search"] = {
            "command": "python3",
            "args": ["-m", "maru_deep_pro_search.server"],
            "env": {},
        }
        write_json_safe(path, config)

        # Also write .claude/settings.json with hooks + hook scripts
        self._write_hooks(scope)
        self._write_settings(scope)
        return True

    # ── inject rules ────────────────────────────────────────────
    def inject_rules(self, scope: str = "user") -> bool:
        # 1. CLAUDE.md
        md_path = self._claude_md_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(md_path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(md_path, new_content)

        # 2. Hook scripts (ensure they exist even if backup restored)
        self._write_hooks(scope)

        # 3. Custom commands
        self._write_commands(scope)
        return True

    # ── helpers ─────────────────────────────────────────────────
    def _write_hooks(self, scope: str) -> None:
        """Install the research-gate hook script that PreToolUse calls."""
        hooks_dir = Path.home() / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        gate_script = hooks_dir / "maru_research_gate.py"
        if not gate_script.exists():
            gate_script.write_text(
                '#!/usr/bin/env python3\n'
                '"""Claude Code PreToolUse hook — blocks Edit/Write without research."""\n'
                'import json, os, sys, time\n\n'
                'def main() -> None:\n'
                '    data = json.load(sys.stdin)\n'
                '    tool_name = data.get("tool_name", "")\n'
                '    if tool_name not in ("Edit", "Write"):\n'
                '        sys.exit(0)\n'
                '    marker = os.path.expanduser("~/.maru/last_research")\n'
                '    if not os.path.exists(marker):\n'
                '        print(json.dumps({\n'
                '            "decision": "deny",\n'
                '            "reason": "[MARU] Research required. Call deep_research(query=...) before editing code."\n'
                '        }))\n'
                '        sys.exit(0)\n'
                '    elapsed = time.time() - os.path.getmtime(marker)\n'
                '    if elapsed > 1800:\n'
                '        print(json.dumps({\n'
                '            "decision": "deny",\n'
                '            "reason": f"[MARU] Research expired ({elapsed/60:.0f}min ago). Re-run deep_research."\n'
                '        }))\n'
                '        sys.exit(0)\n'
                '    sys.exit(0)\n\n'
                'if __name__ == "__main__":\n'
                '    main()\n',
                encoding="utf-8",
            )
            gate_script.chmod(0o755)

    def _write_settings(self, scope: str) -> None:
        path = self._settings_path(scope)
        settings: dict[str, Any] = read_json_safe(path)

        if "hooks" not in settings:
            settings["hooks"] = {}

        # 1. PreToolUse — BLOCK edit/write without research
        if "PreToolUse" not in settings["hooks"]:
            settings["hooks"]["PreToolUse"] = []
        pre_matchers = [h.get("matcher", "") for h in settings["hooks"]["PreToolUse"]]
        if "Edit|Write" not in pre_matchers:
            settings["hooks"]["PreToolUse"].append({
                "matcher": "Edit|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": str(Path.home() / ".claude" / "hooks" / "maru_research_gate.py"),
                    }
                ],
            })

        # 2. PostToolUse — verify citations after edit/write
        if "PostToolUse" not in settings["hooks"]:
            settings["hooks"]["PostToolUse"] = []
        post_matchers = [h.get("matcher", "") for h in settings["hooks"]["PostToolUse"]]
        if "Write|Edit" not in post_matchers:
            settings["hooks"]["PostToolUse"].append({
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "prompt",
                        "prompt": (
                            "You just wrote or edited code. "
                            "Verify that all API references and library versions "
                            "are backed by research citations [1], [2]. "
                            "If not, STOP and call deep_research before continuing."
                        ),
                    }
                ],
            })

        # 3. Permissions — restrict dangerous operations
        if "permissions" not in settings:
            settings["permissions"] = {}
        if "deny" not in settings["permissions"]:
            settings["permissions"]["deny"] = []
        deny_patterns = settings["permissions"]["deny"]
        for pattern in ["rm -rf /*", "DROP TABLE", "format c:", "> /dev/sda"]:
            if pattern not in deny_patterns:
                deny_patterns.append(pattern)

        write_json_safe(path, settings)

    def _write_commands(self, scope: str) -> None:
        cmds_dir = self._commands_dir(scope)
        cmds_dir.mkdir(parents=True, exist_ok=True)

        commands = {
            "research.md": (
                "# /research — Deep research with citations\n\n"
                "Call `deep_research` with the user's current technical intent "
                "and return a synthesized answer with inline citations [1], [2]."
            ),
            "verify.md": (
                "# /verify — Verify code against research\n\n"
                "Review the most recent code changes against the knowledge store. "
                "Confirm all API signatures, versions, and security advice match "
                "the research results. Flag any discrepancies."
            ),
        }

        for filename, content in commands.items():
            cmd_path = cmds_dir / filename
            if not cmd_path.exists():
                cmd_path.write_text(content, encoding="utf-8")
