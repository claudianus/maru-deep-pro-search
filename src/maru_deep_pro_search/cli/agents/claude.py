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
from .base import AgentAdapter, get_mcp_server_command


class ClaudeAdapter(AgentAdapter):
    name = "claude"
    display_name = "Claude Code"

    # ── detect ──────────────────────────────────────────────────
    def detect(self) -> bool:
        return shutil.which("claude") is not None or Path.home().joinpath(".claude").exists()

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

        config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
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
        """Install the research-gate hook scripts that PreToolUse/PostToolUse call."""
        hooks_dir = Path.home() / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # ── PreToolUse gate ──
        gate_script = hooks_dir / "maru_research_gate.py"
        if not gate_script.exists():
            gate_script.write_text(
                "#!/usr/bin/env python3\n"
                '"""Claude Code PreToolUse hook — blocks Bash without research."""\n'
                "import json, os, sys, time\n\n"
                "def main() -> None:\n"
                "    data = json.load(sys.stdin)\n"
                '    tool_name = data.get("tool_name", "")\n'
                "    # PreToolUse exit 2 blocks Bash reliably; Write/Edit have a known\n"
                "    # bug where exit 2 is ignored (github.com/anthropics/claude-code/issues/13744).\n"
                "    # We block Bash here and rely on PostToolUse to revert Write/Edit.\n"
                '    if tool_name != "Bash":\n'
                "        sys.exit(0)\n"
                '    marker = os.path.expanduser("~/.maru/last_research")\n'
                "    if not os.path.exists(marker):\n"
                '        print("[MARU] Research required. Call deep_research(query=...) before running commands.", file=sys.stderr)\n'
                "        sys.exit(2)\n"
                "    elapsed = time.time() - os.path.getmtime(marker)\n"
                "    if elapsed > 1800:\n"
                '        print(f"[MARU] Research expired ({elapsed/60:.0f}min ago). Re-run deep_research.", file=sys.stderr)\n'
                "        sys.exit(2)\n"
                "    sys.exit(0)\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n",
                encoding="utf-8",
            )
            gate_script.chmod(0o755)

        # ── PostToolUse revert script ──
        revert_script = hooks_dir / "maru_research_revert.py"
        if not revert_script.exists():
            revert_script.write_text(
                "#!/usr/bin/env python3\n"
                '"""Claude Code PostToolUse hook — reverts Write/Edit without research.\n'
                "\n"
                "Workaround for PreToolUse exit 2 not blocking Write/Edit:\n"
                "https://github.com/anthropics/claude-code/issues/13744\n"
                '"""\n'
                "import json, os, subprocess, sys\n\n"
                "def main() -> None:\n"
                "    data = json.load(sys.stdin)\n"
                '    tool_name = data.get("tool_name", "")\n'
                '    if tool_name not in ("Write", "Edit"):\n'
                "        sys.exit(0)\n"
                '    marker = os.path.expanduser("~/.maru/last_research")\n'
                "    ok = False\n"
                "    if os.path.exists(marker):\n"
                "        import time\n"
                "        if time.time() - os.path.getmtime(marker) <= 1800:\n"
                "            ok = True\n"
                "    if ok:\n"
                "        sys.exit(0)\n"
                "    # Revert the file change using git checkout\n"
                '    file_path = data.get("tool_input", {}).get("file_path", "")\n'
                "    if file_path:\n"
                '        subprocess.run(["git", "checkout", "--", file_path], capture_output=True)\n'
                '    print("[MARU-POST-GATE] Reverted un-researched edit. Run /research first.", file=sys.stderr)\n'
                "    sys.exit(0)\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n",
                encoding="utf-8",
            )
            revert_script.chmod(0o755)

        # ── SessionStart inject script ──
        session_script = hooks_dir / "maru_session_start.py"
        if not session_script.exists():
            session_script.write_text(
                "#!/usr/bin/env python3\n"
                '"""Claude Code SessionStart hook — inject research reminder."""\n'
                "import json, sys\n\n"
                "def main() -> None:\n"
                "    print(json.dumps({\n"
                '        "additionalContext": "[MARU-RESEARCH-GATE] New session. You MUST run deep_research before any code changes."\n'
                "    }))\n"
                "    sys.exit(0)\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n",
                encoding="utf-8",
            )
            session_script.chmod(0o755)

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
            settings["hooks"]["PreToolUse"].append(
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(
                                Path.home() / ".claude" / "hooks" / "maru_research_gate.py"
                            ),
                        }
                    ],
                }
            )

        # 2. PostToolUse — REVERT un-researched Write/Edit
        #    Workaround for PreToolUse exit 2 not blocking Write/Edit
        #    (github.com/anthropics/claude-code/issues/13744)
        if "PostToolUse" not in settings["hooks"]:
            settings["hooks"]["PostToolUse"] = []
        post_matchers = [h.get("matcher", "") for h in settings["hooks"]["PostToolUse"]]
        if "Write|Edit" not in post_matchers:
            settings["hooks"]["PostToolUse"].append(
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(
                                Path.home() / ".claude" / "hooks" / "maru_research_revert.py"
                            ),
                        }
                    ],
                }
            )

        # 3. SessionStart — inject research reminder
        if "SessionStart" not in settings["hooks"]:
            settings["hooks"]["SessionStart"] = []
        session_matchers = [h.get("matcher", "") for h in settings["hooks"]["SessionStart"]]
        if "*" not in session_matchers:
            settings["hooks"]["SessionStart"].append(
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(
                                Path.home() / ".claude" / "hooks" / "maru_session_start.py"
                            ),
                        }
                    ],
                }
            )

        # 4. UserPromptSubmit — block prompts that try to bypass research
        if "UserPromptSubmit" not in settings["hooks"]:
            settings["hooks"]["UserPromptSubmit"] = []
        ups_matchers = [h.get("matcher", "") for h in settings["hooks"]["UserPromptSubmit"]]
        if "*" not in ups_matchers:
            settings["hooks"]["UserPromptSubmit"].append(
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(
                                Path.home() / ".claude" / "hooks" / "maru_research_gate.py"
                            ),
                        }
                    ],
                }
            )

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
