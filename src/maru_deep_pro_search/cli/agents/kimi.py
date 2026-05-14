"""Kimi Code CLI adapter.

Official docs: https://moonshotai.github.io/kimi-cli/en/configuration/config-files.html

Kimi uses TOML config (~/.kimi/config.toml) with:
- lifecycle hooks (Beta): [[hooks]] array
- MCP client configuration
- providers, models, loop_control, background, services
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
from .base import AgentAdapter, get_mcp_server_command

# ── Kimi PreToolUse hook script ─────────────────────────────────────
_KIMI_HOOK_SCRIPT = '''#!/usr/bin/env python3
"""Kimi PreToolUse hook — blocks edits without research."""
import json
import os
import sys
import time

MARKER = os.path.expanduser("~/.maru/last_research")
TTL_SECONDS = 1800

def main() -> None:
    data = json.load(sys.stdin)
    event = data.get("event", "")
    if event != "PreToolUse":
        sys.exit(0)

    tool = data.get("tool", "")
    if tool not in ("WriteFile", "ApplyDiff", "Shell", "BrowserAction"):
        sys.exit(0)

    if not os.path.exists(MARKER):
        print("[MARU] Research required before editing. Run deep_research first.", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - os.path.getmtime(MARKER)
    if elapsed > TTL_SECONDS:
        print(f"[MARU] Research expired ({elapsed/60:.0f}min). Re-run deep_research.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
'''


class KimiAdapter(AgentAdapter):
    name = "kimi"
    display_name = "Kimi Code CLI"

    def detect(self) -> bool:
        return shutil.which("kimi") is not None or Path.home().joinpath(".kimi").exists()

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".kimi") / "config.toml"
        return Path.home() / ".kimi" / "config.toml"

    def _mcp_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".kimi") / "mcp.json"
        return Path.home() / ".kimi" / "mcp.json"

    def _skills_dir(self, scope: str) -> Path | None:
        if scope == "project":
            return Path(".kimi") / "skills"
        return Path.home() / ".kimi" / "skills"

    skills_format = "nested"

    def backup(self) -> list[Path]:
        paths = [self._config_path("user"), self._mcp_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user"), self._mcp_path("user")]:
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
        config_path = self._config_path(scope)

        # Kimi uses TOML — we manipulate as text
        content = read_text_safe(config_path)
        lines = content.splitlines() if content else []

        # 1. Ensure system_prompt key exists with protocol
        sys_prompt_marker = "# MARU-SYSTEM-PROMPT"
        if sys_prompt_marker not in content:
            # Remove old system_prompt if present
            lines = [ln for ln in lines if not ln.strip().startswith("system_prompt")]
            lines.append('')
            lines.append(sys_prompt_marker)
            lines.append('system_prompt = """')
            for pline in protocol.strip().splitlines():
                lines.append(pline)
            lines.append('"""')

        # 2. Install PreToolUse hook
        hook_script = Path.home() / ".maru" / "kimi_research_gate.py"
        hook_script.parent.mkdir(parents=True, exist_ok=True)
        if not hook_script.exists():
            hook_script.write_text(_KIMI_HOOK_SCRIPT, encoding="utf-8")
            hook_script.chmod(0o755)

        hook_block = f'''[[hooks]]
event = "PreToolUse"
matcher = "WriteFile|ApplyDiff|Shell"
command = "python3 {hook_script}"
timeout = 10'''

        if "[[hooks]]" not in content:
            lines.append('')
            lines.append(hook_block)
        elif hook_script.name not in content:
            # Append after last [[hooks]] block
            lines.append('')
            lines.append(hook_block)

        # 3. Disable default_yolo so research gate can fire
        if "default_yolo" not in content:
            lines.append('')
            lines.append("# MARU: disable auto-approve so research gate works")
            lines.append("default_yolo = false")

        write_text_safe(config_path, "\n".join(lines) + "\n")
        return True
