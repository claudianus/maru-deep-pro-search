"""Cursor adapter — supports .cursorrules, .cursor/mcp.json, settings, commands."""

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
from .base import AgentAdapter, get_mcp_server_command


class CursorAdapter(AgentAdapter):
    name = "cursor"
    display_name = "Cursor"

    def detect(self) -> bool:
        return (
            Path.home().joinpath(".cursor").exists()
            or Path(".cursor").exists()
            or shutil.which("cursor") is not None
        )

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "mcp.json"
        return Path.home() / ".cursor" / "mcp.json"

    def _rules_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursorrules")
        return Path.home() / ".cursorrules"

    def _settings_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "settings.json"
        return Path.home() / ".cursor" / "settings.json"

    def _commands_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "commands"
        return Path.home() / ".cursor" / "commands"

    def _hooks_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".cursor") / "hooks"
        return Path.home() / ".cursor" / "hooks"

    def _skills_dir(self, scope: str) -> Path | None:
        if scope == "project":
            return Path(".cursor") / "rules"
        return Path.home() / ".cursor" / "rules"

    def backup(self) -> list[Path]:
        paths = [self._mcp_path("user"), self._rules_path("user"), self._settings_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._mcp_path("user"), self._rules_path("user"), self._settings_path("user")]:
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
        # 1. .cursorrules
        rules_path = self._rules_path(scope)
        content = read_text_safe(rules_path)
        protocol = get_protocol_for_agent(self.name)

        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(rules_path, new_content)

        # 2. .cursor/settings.json — enable MCP tools by default
        settings_path = self._settings_path(scope)
        settings = read_json_safe(settings_path)
        if "mcp" not in settings:
            settings["mcp"] = {}
        if "autoEnableTools" not in settings["mcp"]:
            settings["mcp"]["autoEnableTools"] = True
        write_json_safe(settings_path, settings)

        # 3. Cursor commands (0.45+ supports custom slash commands)
        cmds_dir = self._commands_dir(scope)
        cmds_dir.mkdir(parents=True, exist_ok=True)

        _write_cursor_command(
            cmds_dir / "research.json",
            name="research",
            description="Run deep research before any code change",
            prompt=(
                "Before writing or modifying any code, you MUST run deep_research "
                "with the user's request as the query. Summarize findings and wait "
                "for user confirmation before proceeding."
            ),
        )
        _write_cursor_command(
            cmds_dir / "verify.json",
            name="verify",
            description="Verify research was completed for this session",
            prompt=(
                "Check if deep_research has been called in this session. "
                "If not, refuse to proceed and instruct the user to run /research first."
            ),
        )

        # 4. .cursor/settings.json — research enforcement hints
        settings_path = self._settings_path(scope)
        settings = read_json_safe(settings_path)
        if "agent" not in settings:
            settings["agent"] = {}
        # Hint to agent that it should always research first
        settings["agent"]["defaultInstructions"] = (
            "You MUST call deep_research before any code generation, file edit, "
            "or architecture decision. This is enforced by the MCP server."
        )
        write_json_safe(settings_path, settings)

        # 5. Cursor Hooks (2026+) — onPreEdit blocks un-researched edits
        hooks_dir = self._hooks_dir(scope)
        hooks_dir.mkdir(parents=True, exist_ok=True)

        pre_edit_script = hooks_dir / "onPreEdit"
        if not pre_edit_script.exists():
            pre_edit_script.write_text(
                "#!/usr/bin/env python3\n"
                '"""Cursor onPreEdit hook — vetoes edits without research."""\n'
                "import json, os, sys, time\n\n"
                "def main() -> None:\n"
                "    # Cursor hooks receive JSON via stdin (tool_name, file_path, etc.)\n"
                "    try:\n"
                "        data = json.load(sys.stdin)\n"
                "    except Exception:\n"
                "        sys.exit(0)\n"
                '    marker = os.path.expanduser("~/.maru/last_research")\n'
                "    if not os.path.exists(marker):\n"
                '        print("[MARU] Research required before editing. Run /research first.", file=sys.stderr)\n'
                "        sys.exit(2)\n"
                "    elapsed = time.time() - os.path.getmtime(marker)\n"
                "    if elapsed > 1800:\n"
                '        print(f"[MARU] Research expired ({elapsed/60:.0f}min). Re-run /research.", file=sys.stderr)\n'
                "        sys.exit(2)\n"
                "    sys.exit(0)\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n",
                encoding="utf-8",
            )
            pre_edit_script.chmod(0o755)

        return True


def _write_cursor_command(path: Path, name: str, description: str, prompt: str) -> None:
    """Write a Cursor custom slash command definition."""
    cmd = {
        "name": name,
        "description": description,
        "prompt": prompt,
    }
    import json

    if not path.exists() or json.loads(path.read_text()).get("prompt") != prompt:
        path.write_text(json.dumps(cmd, indent=2) + "\n")
