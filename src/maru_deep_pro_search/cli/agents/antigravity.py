"""AntiGravity adapter for Antigravity 2.0 and Antigravity CLI."""

from __future__ import annotations

from pathlib import Path

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


class AntiGravityAdapter(AgentAdapter):
    name = "antigravity"
    display_name = "AntiGravity"

    def detect(self) -> bool:
        home = Path.home()
        return (
            home.joinpath(".gemini", "antigravity").exists()
            or home.joinpath(".gemini", "antigravity-cli").exists()
            or home.joinpath(".gemini", "config").exists()
        )

    def _mcp_paths(self, scope: str) -> list[Path]:
        if scope == "project":
            return [
                Path(".gemini") / "antigravity" / "mcp_config.json",
                Path(".agents") / "mcp_config.json",
            ]

        paths = []
        home = Path.home()
        if home.joinpath(".gemini", "config").exists():
            paths.append(home / ".gemini" / "config" / "mcp_config.json")
        if home.joinpath(".gemini", "antigravity-cli").exists():
            paths.append(home / ".gemini" / "antigravity-cli" / "mcp_config.json")
        if home.joinpath(".gemini", "antigravity").exists():
            paths.append(home / ".gemini" / "antigravity" / "mcp_config.json")
        return paths

    def backup(self) -> list[Path]:
        paths = [
            Path.home() / ".gemini" / "config" / "mcp_config.json",
            Path.home() / ".gemini" / "config" / "hooks.json",
            Path.home() / ".gemini" / "antigravity-cli" / "mcp_config.json",
            Path.home() / ".gemini" / "antigravity-cli" / "settings.json",
            Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        ]
        backups = [backup_file(p) for p in paths if p.exists()]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        paths = [
            Path.home() / ".gemini" / "config" / "mcp_config.json",
            Path.home() / ".gemini" / "config" / "hooks.json",
            Path.home() / ".gemini" / "antigravity-cli" / "mcp_config.json",
            Path.home() / ".gemini" / "antigravity-cli" / "settings.json",
            Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        ]
        restored = False
        for p in paths:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    def install_mcp(self, scope: str = "user") -> bool:
        paths = self._mcp_paths(scope)
        for path in paths:
            config = read_json_safe(path)
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            config["mcpServers"]["maru-deep-pro-search"] = get_mcp_server_command()
            config.pop("_maru_deep_pro_search_notes", None)
            write_json_safe(path, config)

        if scope == "user":
            self._configure_cli_permissions()

        return True

    def _configure_cli_permissions(self) -> None:
        path = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
        if not path.exists():
            return
        settings = read_json_safe(path)
        if "permissions" not in settings:
            settings["permissions"] = {}
        if "allow" not in settings["permissions"]:
            settings["permissions"]["allow"] = []

        allow_list = settings["permissions"]["allow"]
        target = "mcp(maru-deep-pro-search/*)"
        if target not in allow_list:
            allow_list.append(target)
            write_json_safe(path, settings)

    def inject_rules(self, scope: str = "user", *, repair: bool = False) -> bool:
        protocol = get_protocol_for_agent(self.name)

        # 1. Global rules path for Antigravity 2.0 (if config exists)
        if scope == "user":
            rules_dir = Path.home() / ".gemini" / "config" / "rules"
            if rules_dir.parent.exists():
                rules_dir.mkdir(parents=True, exist_ok=True)
                rule_file = rules_dir / "maru-research-protocol.md"
                content = read_text_safe(rule_file)
                new_content = inject_protocol(content, protocol)
                if new_content != content:
                    write_text_safe(rule_file, new_content)

        # 2. Legacy rules path for older desktop version (if antigravity folder exists)
        legacy_dir = Path.home() / ".gemini" / "antigravity"
        if legacy_dir.exists():
            sidecar = legacy_dir / "MARU_RESEARCH_PROTOCOL.md"
            content = read_text_safe(sidecar)
            new_content = inject_protocol(content, protocol)
            if new_content != content:
                write_text_safe(sidecar, new_content)

        # 3. Write hook script and register in hooks.json (Antigravity 2.0 PreToolUse Hook)
        self._install_hooks(scope, repair=repair)
        return True

    def refresh_managed_hooks(self, *, repair: bool = False) -> bool:
        self._install_hooks("user", repair=repair)
        return True

    def _install_hooks(self, scope: str, *, repair: bool = False) -> None:
        """Install Antigravity hooks for research gating."""
        if scope == "project":
            hooks_dir = Path(".agents")
            hooks_path = hooks_dir / "hooks.json"
            hooks_dir.mkdir(parents=True, exist_ok=True)
        else:
            hooks_dir = Path.home() / ".gemini" / "config"
            hooks_path = hooks_dir / "hooks.json"
            if not hooks_dir.exists():
                if hooks_dir.parent.exists():
                    hooks_dir.mkdir(parents=True, exist_ok=True)
                else:
                    return

        # Write the gate script to ~/.maru/
        gate_script = Path.home() / ".maru" / "antigravity_research_gate.py"
        write_managed_hook(
            gate_script,
            template_body("antigravity_research_gate"),
            force=repair,
        )

        hooks = read_json_safe(hooks_path)
        if "maru-research-gate" not in hooks:
            hooks["maru-research-gate"] = {}

        group = hooks["maru-research-gate"]
        if "PreToolUse" not in group:
            group["PreToolUse"] = []

        old_matcher = "run_command|write_to_file|replace_file_content|multi_replace_file_content"
        group["PreToolUse"] = [
            entry for entry in group["PreToolUse"] if entry.get("matcher") != old_matcher
        ]
        matcher = "run_command|search_web|google_search|brave_search|chrome-devtools-mcp"
        found = False
        for entry in group["PreToolUse"]:
            if entry.get("matcher") == matcher:
                if "hooks" not in entry:
                    entry["hooks"] = []
                existing_cmds = [h.get("command", "") for h in entry["hooks"]]
                if str(gate_script) not in existing_cmds:
                    entry["hooks"].append(
                        {
                            "type": "command",
                            "command": str(gate_script),
                        }
                    )
                found = True
                break

        if not found:
            group["PreToolUse"].append(
                {
                    "matcher": matcher,
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(gate_script),
                        }
                    ],
                }
            )

        write_json_safe(hooks_path, hooks)
