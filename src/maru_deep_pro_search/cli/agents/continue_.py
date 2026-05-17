"""Continue adapter — config.yaml (preferred) and legacy config.json.

Official docs:
- https://docs.continue.dev/customize/deep-dives/configuration
- https://docs.continue.dev/reference/yaml-migration
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

import yaml

from ..backup import backup_file, read_json_safe, restore_file, sorted_backup_paths, write_json_safe
from ..idempotent import yaml_rule_has_protocol
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter, get_continue_experimental_mcp_entry, get_mcp_server_command


class ContinueAdapter(AgentAdapter):
    name = "continue"
    display_name = "Continue"

    def detect(self) -> bool:
        return (
            shutil.which("continue") is not None
            or Path.home().joinpath(".continue", "config.yaml").exists()
            or Path.home().joinpath(".continue", "config.json").exists()
            or Path.home().joinpath(".config", "continue", "config.json").exists()
        )

    def _yaml_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".continue") / "config.yaml"
        return Path.home() / ".continue" / "config.yaml"

    def _json_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".continue") / "config.json"
        legacy = Path.home() / ".config" / "continue" / "config.json"
        primary = Path.home() / ".continue" / "config.json"
        return primary if primary.exists() or not legacy.exists() else legacy

    def _resolve_config(self, scope: str) -> tuple[str, Path]:
        yaml_path = self._yaml_path(scope)
        json_path = self._json_path(scope)
        if yaml_path.exists():
            return "yaml", yaml_path
        if json_path.exists():
            return "json", json_path
        return "yaml", yaml_path

    def _ignore_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".continueignore")
        return Path.home() / ".continueignore"

    def _skills_dir(self, scope: str) -> Path | None:
        if scope == "project":
            return Path(".continue") / "rules"
        return Path.home() / ".continue" / "rules"

    skills_format = "flat"

    def backup(self) -> list[Path]:
        backups: list[Path] = []
        for path in (self._yaml_path("user"), self._json_path("user")):
            b = backup_file(path)
            if b is not None:
                backups.append(b)
        return backups

    def restore(self) -> bool:
        restored = False
        for path in (self._yaml_path("user"), self._json_path("user")):
            backs = sorted_backup_paths(path)
            if backs:
                restored = restore_file(path, backs[0]) or restored
        return restored

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _write_yaml(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def install_mcp(self, scope: str = "user") -> bool:
        kind, path = self._resolve_config(scope)
        if kind == "yaml":
            data = self._load_yaml(path)
            mcp = data.setdefault("mcpServers", {})
            if not isinstance(mcp, dict):
                mcp = {}
                data["mcpServers"] = mcp
            mcp["maru-deep-pro-search"] = get_mcp_server_command()
            self._write_yaml(path, data)
            return True

        config = read_json_safe(path)
        if isinstance(config.get("mcpServers"), dict):
            servers = cast(dict[str, Any], config["mcpServers"])
        else:
            servers = {}
            config["mcpServers"] = servers
        servers["maru-deep-pro-search"] = get_mcp_server_command()

        experimental = config.setdefault("experimental", {})
        if isinstance(experimental, dict):
            mcp_list = experimental.setdefault("modelContextProtocolServers", [])
            if not isinstance(mcp_list, list):
                mcp_list = []
                experimental["modelContextProtocolServers"] = mcp_list
            if not any(
                isinstance(e, dict) and e.get("name") == "maru-deep-pro-search" for e in mcp_list
            ):
                entry = get_continue_experimental_mcp_entry()
                entry["name"] = "maru-deep-pro-search"
                mcp_list.append(entry)

        if isinstance(config.get("server"), dict):
            server = cast(dict[str, Any], config["server"])
            server.pop("mcpServers", None)
            if not server:
                config.pop("server", None)

        write_json_safe(path, config)
        return True

    @staticmethod
    def _research_prompts() -> list[dict[str, str]]:
        return [
            {
                "name": "ask",
                "description": "Answer a general web question with live sources",
                "prompt": (
                    'Call answer with the user\'s current question, mode="balanced". '
                    "Use the returned evidence packet to answer directly with inline "
                    "citations [1], [2]. Use this for current facts, prices, "
                    "recommendations, and Korean consumer searches."
                ),
            },
            {
                "name": "search",
                "description": "Run targeted web search",
                "prompt": (
                    "Extract a concise keyword query from the user's request and call "
                    "web_search. Return ranked sources with citation IDs and note which "
                    "results should be fetched next."
                ),
            },
            {
                "name": "compare",
                "description": "Run comparative parallel search",
                "prompt": (
                    "Convert the user's comparison into 2-5 independent keyword queries "
                    "and call parallel_search with comparison_mode=true. Summarize the "
                    "strongest evidence with citations."
                ),
            },
            {
                "name": "research",
                "description": "Run deep research before any code change",
                "prompt": (
                    "Before writing or modifying any code, extract 3-12 search "
                    "keywords from the user's technical intent and call deep_research. "
                    "Summarize findings and wait for confirmation before proceeding. "
                    "Use /ask for ordinary web questions."
                ),
            },
            {
                "name": "verify",
                "description": "Verify research was completed for this session",
                "prompt": (
                    "Check if deep_research has been called in this session. "
                    "If not, refuse to proceed and instruct the user to run "
                    "/research first."
                ),
            },
        ]

    def _inject_yaml_rules(self, data: dict[str, Any], protocol: str) -> None:
        rules = data.setdefault("rules", [])
        if not isinstance(rules, list):
            rules = []
            data["rules"] = rules
        for i, rule in enumerate(list(rules)):
            if yaml_rule_has_protocol(rule):
                new_r = inject_protocol(cast(str, rule), protocol)
                if new_r != rule:
                    rules[i] = new_r
                break
        else:
            rules.append(protocol)

        prompts = data.setdefault("prompts", [])
        if not isinstance(prompts, list):
            prompts = []
            data["prompts"] = prompts

        def _has_name(name: str) -> bool:
            return any(isinstance(p, dict) and p.get("name") == name for p in prompts)

        for spec in self._research_prompts():
            if not _has_name(spec["name"]):
                prompts.append(spec)

    def inject_rules(self, scope: str = "user") -> bool:
        protocol = get_protocol_for_agent(self.name)
        kind, path = self._resolve_config(scope)

        if kind == "yaml":
            data = self._load_yaml(path)
            self._inject_yaml_rules(data, protocol)
            self._write_yaml(path, data)
        else:
            config = read_json_safe(path)
            if "custom_commands" not in config:
                config["custom_commands"] = []
            cmds = cast(list[Any], config["custom_commands"])
            names = [c.get("name", "") for c in cmds if isinstance(c, dict)]
            for spec in self._research_prompts():
                if spec["name"] not in names:
                    cmds.append(spec)

            current = config.get("system_message", "")
            if isinstance(current, str):
                new_prompt = inject_protocol(current, protocol)
                if new_prompt != current:
                    config["system_message"] = new_prompt
            write_json_safe(path, config)

        ignore_path = self._ignore_path(scope)
        if not ignore_path.exists():
            ignore_path.write_text(
                ".maru/knowledge.db\n.maru/knowledge.db-journal\n",
                encoding="utf-8",
            )
        return True

    def verify_setup(self, scope: str = "user") -> dict[str, bool]:
        from ..verify_status import json_mcp_ok, rules_text_ok, yaml_mcp_ok

        kind, path = self._resolve_config(scope)
        if kind == "yaml":
            data = self._load_yaml(path)
            rules = data.get("rules", [])
            rules_ok = isinstance(rules, list) and any(yaml_rule_has_protocol(r) for r in rules)
            return {"mcp": yaml_mcp_ok(data), "rules": rules_ok}

        config = read_json_safe(path)
        sys_msg = config.get("system_message", "")
        rules_ok = isinstance(sys_msg, str) and rules_text_ok(sys_msg)
        return {"mcp": json_mcp_ok(config), "rules": rules_ok}
