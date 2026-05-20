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
    sorted_backup_paths,
    write_json_safe,
    write_text_safe,
)
from ..hooks_templates import (
    template_body,
    write_managed_hook,
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

    def _skills_dir(self, scope: str) -> Path | None:
        if scope == "project":
            return Path(".claude") / "skills"
        return Path.home() / ".claude" / "skills"

    skills_format = "nested"

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
            backups = sorted_backup_paths(p)
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
        self._write_hooks()
        self._write_settings(scope)
        return True

    # ── inject rules ────────────────────────────────────────────
    def inject_rules(self, scope: str = "user", *, repair: bool = False) -> bool:
        # 1. CLAUDE.md
        md_path = self._claude_md_path(scope)
        protocol = get_protocol_for_agent(self.name)
        content = read_text_safe(md_path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(md_path, new_content)

        # 2. Hook scripts (ensure they exist even if backup restored)
        self._write_hooks(repair=repair)

        # 3. Custom commands
        self._write_commands(scope)
        return True

    def refresh_managed_hooks(self, *, repair: bool = False) -> bool:
        self._write_hooks(repair=repair)
        return True

    # ── helpers ─────────────────────────────────────────────────
    def _write_hooks(self, *, repair: bool = False) -> None:
        """Install freshness-gate hook scripts."""
        hooks_dir = Path.home() / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        write_managed_hook(
            hooks_dir / "maru_research_gate.py",
            template_body("claude_research_gate"),
            force=repair,
        )
        write_managed_hook(
            hooks_dir / "maru_research_revert.py",
            template_body("claude_research_revert"),
            force=repair,
        )
        write_managed_hook(
            hooks_dir / "maru_session_start.py",
            template_body("claude_session_start"),
            force=repair,
        )

    def _write_settings(self, scope: str) -> None:
        path = self._settings_path(scope)
        settings: dict[str, Any] = read_json_safe(path)

        if "hooks" not in settings:
            settings["hooks"] = {}

        # 1. PreToolUse — gate only freshness-sensitive search/network actions.
        if "PreToolUse" not in settings["hooks"]:
            settings["hooks"]["PreToolUse"] = []
        # Migrate old edit gates away from broad research enforcement.
        settings["hooks"]["PreToolUse"] = [
            h
            for h in settings["hooks"]["PreToolUse"]
            if h.get("matcher") not in {"Edit|Write", "Edit|Write|WebSearch|WebFetch"}
        ]
        pre_matchers = [h.get("matcher", "") for h in settings["hooks"]["PreToolUse"]]
        target_matcher = "Bash|WebSearch|WebFetch"
        if target_matcher not in pre_matchers:
            settings["hooks"]["PreToolUse"].append(
                {
                    "matcher": target_matcher,
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

        # 2. Remove old PostToolUse edit-revert gates. Research freshness should not undo
        # local edits; only external freshness-sensitive actions are gated.
        if "PostToolUse" not in settings["hooks"]:
            settings["hooks"]["PostToolUse"] = []
        settings["hooks"]["PostToolUse"] = [
            h for h in settings["hooks"]["PostToolUse"] if h.get("matcher") != "Write|Edit"
        ]

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
            "ask.md": (
                "# /ask — Perplexity-style live web answer\n\n"
                'Call `answer` with the user\'s current question, `mode="balanced"`, '
                "and synthesize a direct response with inline citations [1], [2]. "
                "Use this for current facts, prices, recommendations, and Korean "
                "consumer searches such as 중고폰 시세 or 노트북 추천."
            ),
            "search.md": (
                "# /search — Targeted source search\n\n"
                "Extract a concise keyword query from the user's request and call "
                "`web_search`. Return ranked sources with citation IDs and note "
                "which results should be fetched next."
            ),
            "compare.md": (
                "# /compare — Multi-angle comparison search\n\n"
                "Convert the user's comparison into 2-5 independent keyword queries "
                "and call `parallel_search` with `comparison_mode=true`. Summarize "
                "the strongest evidence and cite sources."
            ),
            "research.md": (
                "# /research — Deep research with citations\n\n"
                "Extract 3-12 search keywords from the user's current technical "
                "intent, call `deep_research`, and return a synthesized answer "
                "with inline citations [1], [2]. Use /ask for ordinary web questions."
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
            existing = ""
            if cmd_path.exists():
                try:
                    existing = cmd_path.read_text(encoding="utf-8")
                except OSError:
                    existing = ""
            if existing != content:
                cmd_path.write_text(content, encoding="utf-8")
