"""Hermes (Nous Research) adapter — plugin-based enforcement.

Hermes has the richest plugin system of any agent we support:

- ``pre_tool_call`` / ``post_tool_call`` hooks
- ``on_session_start`` / ``on_session_end`` lifecycle hooks
- ``pre_llm_call`` / ``post_llm_call`` turn hooks
- ``ctx.register_command()`` for slash commands
- ``ctx.register_cli_command()`` for CLI subcommands
- ``ctx.inject_message()`` for in-conversation messaging
- ``ctx.dispatch_tool()`` for programmatic tool invocation
- pip entry-point discovery via ``hermes_agent.plugins``
- MCP server auto-discovery via ``config.yaml``
- Gateway hooks via ``~/.hermes/hooks/``
- Shell hooks via ``config.yaml``

This adapter leverages **all** of these surfaces:

1. **MCP** — registers maru-deep-pro-search in ``~/.hermes/config.yaml``
2. **Plugin** — installs the bundled ``maru-research-gate`` plugin
3. **Shell hooks** — adds audit-log shell triggers
4. **Gateway hooks** — adds message-filter gateway hook
5. **Skills** — registers the research-first skill
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
from ..prompts import get_protocol_for_agent
from .base import AgentAdapter, get_mcp_server_yaml


class HermesAdapter(AgentAdapter):
    name = "hermes"
    display_name = "Hermes (Nous Research)"

    def detect(self) -> bool:
        return shutil.which("hermes") is not None or Path.home().joinpath(".hermes").exists()

    # ── paths ────────────────────────────────────────────────────
    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".hermes") / "config.yaml"
        return Path.home() / ".hermes" / "config.yaml"

    def _plugins_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".hermes") / "plugins"
        return Path.home() / ".hermes" / "plugins"

    def _hooks_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".hermes") / "hooks"
        return Path.home() / ".hermes" / "hooks"

    def _soul_md_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("SOUL.md")
        return Path.home() / ".hermes" / "SOUL.md"

    def _skills_dir(self, scope: str) -> Path:
        if scope == "project":
            return Path(".hermes") / "skills"
        return Path.home() / ".hermes" / "skills"

    def backup(self) -> list[Path]:
        paths = [self._config_path("user")]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [self._config_path("user")]:
            backups = sorted(p.parent.glob(f"{p.name}.bak.*"), reverse=True)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    # ── install MCP ──────────────────────────────────────────────
    def install_mcp(self, scope: str = "user") -> bool:
        config_path = self._config_path(scope)
        # Hermes uses YAML config — we read/write as text with safe append
        content = read_text_safe(config_path) or ""

        # Ensure mcp_servers section
        if "mcp_servers" not in content:
            content += "\nmcp_servers:\n"

        marker = "# maru-deep-pro-search MCP"
        if marker not in content:
            content += f"\n{marker}\n" + get_mcp_server_yaml()
            write_text_safe(config_path, content)

        return True

    # ── inject rules ─────────────────────────────────────────────
    def inject_rules(self, scope: str = "user") -> bool:
        protocol = get_protocol_for_agent(self.name)

        # 1. SOUL.md — Hermes primary agent identity (slot #1 in system prompt)
        soul_path = self._soul_md_path(scope)
        soul_content = read_text_safe(soul_path)
        new_soul = inject_protocol(soul_content, protocol)
        if new_soul != soul_content:
            write_text_safe(soul_path, new_soul)

        # 2. config.yaml — enable plugin + shell hooks + skills
        config_path = self._config_path(scope)
        content = read_text_safe(config_path) or ""

        # Inject protocol as YAML comment block
        protocol = get_protocol_for_agent(self.name)
        protocol_yaml = (
            "# MARU-RESEARCH-PROTOCOL-START\n"
            + "\n".join(f"# {line}" for line in protocol.splitlines())
            + "\n# MARU-RESEARCH-PROTOCOL-END\n"
        )
        if "MARU-RESEARCH-PROTOCOL-START" not in content:
            content = protocol_yaml + "\n" + content

        # Enable our plugin (idempotent: won't duplicate)
        lines = content.splitlines()
        plugins_idx = None
        enabled_idx = None
        maru_present = False

        for i, line in enumerate(lines):
            if line.rstrip() == "plugins:":
                plugins_idx = i
            if plugins_idx is not None and line.strip() == "enabled:":
                enabled_idx = i
            if "maru-research-gate" in line:
                maru_present = True

        if plugins_idx is None:
            lines.append("plugins:")
            lines.append("  enabled:")
            lines.append("    - maru-research-gate")
        elif enabled_idx is None:
            lines.insert(plugins_idx + 1, "  enabled:")
            lines.insert(plugins_idx + 2, "    - maru-research-gate")
        elif not maru_present:
            lines.insert(enabled_idx + 1, "    - maru-research-gate")

        content = "\n".join(lines) + "\n"

        # Shell hooks for audit logging
        shell_hook_marker = "# maru-shell-hooks"
        if shell_hook_marker not in content:
            content += (
                f"\n{shell_hook_marker}\n"
                "hooks:\n"
                "  post_tool_call:\n"
                "    - command: echo\n"
                '      args: ["[MARU-AUDIT] tool executed"]\n'
            )

        write_text_safe(config_path, content)

        # 3. Plugin directory — write plugin.yaml + __init__.py
        plugin_dir = self._plugins_dir(scope) / "maru-research-gate"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        plugin_yaml = plugin_dir / "plugin.yaml"
        if not plugin_yaml.exists():
            plugin_yaml.write_text(
                "name: maru-research-gate\n"
                'version: "1.0"\n'
                "description: >\n"
                "  Blocks un-researched tool calls via pre_tool_call hook.\n"
                "  Provides /research and /verify slash commands.\n"
                "  Distributed as part of maru-deep-pro-search.\n"
            )

        # The actual plugin code lives in our package; we symlink it
        plugin_init = plugin_dir / "__init__.py"
        if not plugin_init.exists():
            # Write a thin shim that imports from our package
            plugin_init.write_text(
                '"""Hermes research gate plugin — auto-generated by maru setup."""\n'
                "\n"
                "try:\n"
                "    from maru_deep_pro_search.cli.agents.hermes_plugin import register\n"
                "except Exception as exc:\n"
                "    import warnings\n"
                '    warnings.warn(f"maru plugin import failed: {exc}")\n'
                "\n"
                "    def register(ctx):\n"
                '        ctx.inject_message("[MARU] Plugin import failed. "\n'
                '                           "Is maru-deep-pro-search installed?",\n'
                '                           role="system")\n'
            )

        # 4. Gateway hook — message filter
        gateway_hook_dir = self._hooks_dir(scope) / "maru-research-gate"
        gateway_hook_dir.mkdir(parents=True, exist_ok=True)

        hook_yaml = gateway_hook_dir / "HOOK.yaml"
        if not hook_yaml.exists():
            hook_yaml.write_text(
                "name: maru-research-gate\nevents:\n  - session:start\n  - agent:end\n"
            )

        hook_handler = gateway_hook_dir / "handler.py"
        if not hook_handler.exists():
            hook_handler.write_text(
                '"""Gateway hook handler for maru research gate."""\n'
                "\n"
                "def handle(event, context):\n"
                "    if event == 'session:start':\n"
                '        return {"action": "inject", "message": "[MARU] New session. "\n'
                '                "Run /research before any tools."}\n'
                "    return None\n"
            )

        # 5. Skill registration
        skills_dir = self._skills_dir(scope)
        skills_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skills_dir / "research-first.md"
        if not skill_file.exists():
            skill_file.write_text(
                "# Skill: Research First\n\n"
                "Before any tool call except `deep_research`, verify that\n"
                "a research session has been completed in the current turn.\n"
                "If not, refuse to proceed and instruct the user to run\n"
                "`/research <query>`.\n"
            )

        return True
