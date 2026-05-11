"""Plugin system for team-shared harness configurations.

A plugin is a directory (or git repo) containing:
    plugin.yaml         # metadata
    commands/           # custom commands
    rules/              # path-based rules
    hooks.yaml          # lifecycle hooks
    mcp.yaml            # MCP server definitions
    conventions.md      # coding conventions

Plugins are installed to `.maru/plugins/<name>/` and merged into
the project's HarnessSpec during `init` or `setup`.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .spec import AgentCommand, AgentRule, HarnessSpec, LifecycleHook

logger = logging.getLogger("maru_deep_pro_search.harness.plugin")


@dataclass
class Plugin:
    """A single harness plugin."""

    name: str
    version: str
    description: str
    agents: list[str]  # which agents this plugin targets
    commands: list[AgentCommand] = field(default_factory=list)
    rules: list[AgentRule] = field(default_factory=list)
    hooks: list[LifecycleHook] = field(default_factory=list)
    mcp_servers: dict[str, dict[str, Any]] = field(default_factory=dict)
    conventions: list[str] = field(default_factory=list)
    conventions_content: str = ""

    @classmethod
    def from_directory(cls, path: Path | str) -> Plugin:
        """Load a plugin from a directory."""
        root = Path(path)

        # 1. Metadata
        meta_path = root / "plugin.yaml"
        if not meta_path.exists():
            meta_path = root / "plugin.json"

        if meta_path.exists():
            if meta_path.suffix == ".yaml":
                import yaml

                meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            else:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            meta = {"name": root.name, "version": "0.1.0", "description": "", "agents": []}

        # 2. Commands
        commands: list[AgentCommand] = []
        cmds_dir = root / "commands"
        if cmds_dir.exists():
            for cmd_file in sorted(cmds_dir.glob("*.md")):
                text = cmd_file.read_text(encoding="utf-8")
                lines = text.splitlines()
                name = cmd_file.stem
                description = lines[0].lstrip("#").strip() if lines else name
                prompt = "\n".join(lines[1:]).strip() if len(lines) > 1 else text
                commands.append(AgentCommand(name=name, description=description, prompt=prompt))

        # 3. Rules
        rules: list[AgentRule] = []
        rules_dir = root / "rules"
        if rules_dir.exists():
            for rule_file in sorted(rules_dir.glob("*.md")):
                text = rule_file.read_text(encoding="utf-8")
                scope = rule_file.stem  # e.g. "global.md", "python.md" -> "global", "python"
                rules.append(AgentRule(scope=scope, content=text))

        # 4. Hooks
        hooks: list[LifecycleHook] = []
        hooks_path = root / "hooks.yaml"
        if hooks_path.exists():
            import yaml

            hooks_data = yaml.safe_load(hooks_path.read_text(encoding="utf-8"))
            for h in hooks_data or []:
                hooks.append(LifecycleHook(**h))

        # 5. MCP servers
        mcp_path = root / "mcp.yaml"
        mcp_servers: dict[str, dict[str, Any]] = {}
        if mcp_path.exists():
            import yaml

            mcp_servers = yaml.safe_load(mcp_path.read_text(encoding="utf-8")) or {}

        # 6. Conventions
        conventions: list[str] = []
        conventions_content = ""
        conv_path = root / "conventions.md"
        if conv_path.exists():
            conventions.append(str(conv_path))
            conventions_content = conv_path.read_text(encoding="utf-8")

        return cls(
            name=meta.get("name", root.name),
            version=meta.get("version", "0.1.0"),
            description=meta.get("description", ""),
            agents=meta.get("agents", []),
            commands=commands,
            rules=rules,
            hooks=hooks,
            mcp_servers=mcp_servers,
            conventions=conventions,
            conventions_content=conventions_content,
        )

    def merge_into(self, spec: HarnessSpec) -> HarnessSpec:
        """Merge this plugin into a HarnessSpec, returning a new spec."""
        # Deep-copy-ish merge
        spec.commands.extend(self.commands)
        spec.rules.extend(self.rules)
        spec.hooks.extend(self.hooks)
        spec.mcp_servers.update(self.mcp_servers)
        spec.conventions.extend(self.conventions)
        if self.conventions_content:
            spec.research_protocol += "\n\n" + self.conventions_content
        return spec


class PluginManager:
    """Manages plugins in `.maru/plugins/`."""

    def __init__(self, project_root: Path | str = ".") -> None:
        self.root = Path(project_root).resolve()
        self.plugins_dir = self.root / ".maru" / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def list_plugins(self) -> list[Plugin]:
        """Return all installed plugins."""
        plugins: list[Plugin] = []
        for subdir in sorted(self.plugins_dir.iterdir()):
            if subdir.is_dir():
                try:
                    plugins.append(Plugin.from_directory(subdir))
                except Exception as exc:
                    logger.warning("Failed to load plugin %s: %s", subdir.name, exc)
        return plugins

    def install(self, source: str) -> Plugin:
        """Install a plugin from a git URL or local path."""
        from urllib.parse import urlparse

        is_git = urlparse(source).scheme in ("http", "https", "ssh", "git")

        if is_git:
            name = Path(source).stem.replace("maru-plugin-", "").replace("maru-harness-", "")
            target = self.plugins_dir / name
            if target.exists():
                shutil.rmtree(target)
            subprocess.run(
                ["git", "clone", "--depth", "1", source, str(target)],
                check=True,
                capture_output=True,
            )
            plugin = Plugin.from_directory(target)
        else:
            src = Path(source)
            if not src.exists():
                raise FileNotFoundError(f"Plugin source not found: {source}")
            name = src.name
            target = self.plugins_dir / name
            if target.exists():
                shutil.rmtree(target)
            if src.is_dir():
                shutil.copytree(src, target)
            else:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target / src.name)
            plugin = Plugin.from_directory(target)

        logger.info("Installed plugin %s v%s", plugin.name, plugin.version)
        return plugin

    def uninstall(self, name: str) -> bool:
        """Remove a plugin."""
        target = self.plugins_dir / name
        if target.exists():
            shutil.rmtree(target)
            logger.info("Uninstalled plugin %s", name)
            return True
        return False

    def get_merged_spec(self, base: HarnessSpec | None = None) -> HarnessSpec:
        """Return a HarnessSpec with all installed plugins merged."""
        spec = base or HarnessSpec.default()
        for plugin in self.list_plugins():
            spec = plugin.merge_into(spec)
        return spec


# Lazy import to avoid circular deps
import subprocess  # noqa: E402
