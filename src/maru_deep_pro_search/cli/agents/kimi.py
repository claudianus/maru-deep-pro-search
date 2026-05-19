"""Kimi Code CLI adapter.

Official docs: https://moonshotai.github.io/kimi-cli/en/configuration/config-files.html

Kimi uses TOML config (~/.kimi/config.toml) with:
- lifecycle hooks (Beta): [[hooks]] array
- MCP client configuration
- providers, models, loop_control, background, services
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..backup import (
    backup_file,
    read_text_safe,
    restore_file,
    sorted_backup_paths,
    write_text_safe,
)
from ..hooks_templates import template_body, write_managed_hook
from ..prompts import get_protocol_for_agent
from .base import AgentAdapter, get_mcp_server_command
from .kimi_toml import upsert_default_yolo_false, upsert_kimi_hook_block, upsert_kimi_system_prompt


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
            backups = sorted_backup_paths(p)
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

    def refresh_managed_hooks(self, *, repair: bool = False) -> bool:
        hook_script = Path.home() / ".maru" / "kimi_research_gate.py"
        write_managed_hook(hook_script, template_body("kimi_research_gate"), force=repair)
        return True

    def inject_rules(self, scope: str = "user", *, repair: bool = False) -> bool:
        protocol = get_protocol_for_agent(self.name)
        config_path = self._config_path(scope)

        content = read_text_safe(config_path)
        content = re.sub(r"^\s*hooks\s*=\s*\[\s*\]\s*(#.*)?$", "", content, flags=re.MULTILINE)
        content = upsert_kimi_system_prompt(content, protocol)

        hook_script = Path.home() / ".maru" / "kimi_research_gate.py"
        write_managed_hook(hook_script, template_body("kimi_research_gate"), force=repair)

        hook_block = f"""[[hooks]]
event = "PreToolUse"
matcher = "WriteFile|ApplyDiff|Shell"
command = "python3 {hook_script}"
timeout = 10"""
        content = upsert_kimi_hook_block(content, hook_block)

        content = upsert_default_yolo_false(content)

        write_text_safe(config_path, content)
        return True
