"""Tests for the harness plugin system."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from maru_deep_pro_search.harness.plugin import Plugin, PluginManager
from maru_deep_pro_search.harness.spec import HarnessSpec


@pytest.fixture(autouse=True)
def _mock_yaml(monkeypatch):
    """Provide a minimal yaml mock since pyyaml is not a project dependency."""
    yaml_mod = MagicMock()

    def _fake_safe_load(s):
        s_str = s.read_text(encoding="utf-8") if hasattr(s, "read_text") else str(s)
        stripped = s_str.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return json.loads(stripped)
        return {}

    yaml_mod.safe_load = _fake_safe_load
    monkeypatch.setitem(sys.modules, "yaml", yaml_mod)
    yield


@pytest.fixture
def plugin_dir(tmp_path: Path) -> Path:
    """Create a minimal plugin directory with all supported files."""
    root = tmp_path / "my-plugin"
    root.mkdir()

    (root / "plugin.json").write_text(
        json.dumps(
            {
                "name": "my-plugin",
                "version": "1.0.0",
                "description": "A test plugin",
                "agents": ["claude", "cursor"],
            }
        ),
        encoding="utf-8",
    )

    cmds = root / "commands"
    cmds.mkdir()
    (cmds / "research.md").write_text("# Research\nDo deep research.", encoding="utf-8")

    rules = root / "rules"
    rules.mkdir()
    (rules / "python.md").write_text("Always type hint.", encoding="utf-8")

    hooks = root / "hooks.yaml"
    hooks.write_text(
        json.dumps(
            [
                {
                    "event": "post_tool_use",
                    "matcher": "Write",
                    "action": "prompt",
                    "prompt": "Check citations",
                }
            ]
        ),
        encoding="utf-8",
    )

    mcp = root / "mcp.yaml"
    mcp.write_text(json.dumps({"my-server": {"command": "python3"}}), encoding="utf-8")

    conv = root / "conventions.md"
    conv.write_text("Use black.", encoding="utf-8")

    return root


class TestPluginFromDirectory:
    def test_loads_all_components(self, plugin_dir: Path) -> None:
        p = Plugin.from_directory(plugin_dir)
        assert p.name == "my-plugin"
        assert p.version == "1.0.0"
        assert p.description == "A test plugin"
        assert p.agents == ["claude", "cursor"]
        assert len(p.commands) == 1
        assert p.commands[0].name == "research"
        assert p.commands[0].description == "Research"
        assert p.commands[0].prompt == "Do deep research."
        assert len(p.rules) == 1
        assert p.rules[0].scope == "python"
        assert p.rules[0].content == "Always type hint."
        assert len(p.hooks) == 1
        assert p.hooks[0].event == "post_tool_use"
        assert p.mcp_servers == {"my-server": {"command": "python3"}}
        assert p.conventions == [str(plugin_dir / "conventions.md")]
        assert p.conventions_content == "Use black."

    def test_fallback_when_no_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "bare"
        root.mkdir()
        p = Plugin.from_directory(root)
        assert p.name == "bare"
        assert p.version == "0.1.0"
        assert p.agents == []

    def test_yaml_metadata(self, tmp_path: Path, monkeypatch) -> None:
        root = tmp_path / "yaml-plugin"
        root.mkdir()
        meta = root / "plugin.yaml"
        meta.write_text('name: yaml-plugin\nversion: "2.0.0"\nagents: [claude]\n')

        yaml_mod = MagicMock()
        yaml_mod.safe_load = lambda s: {
            "name": "yaml-plugin",
            "version": "2.0.0",
            "agents": ["claude"],
        }
        monkeypatch.setitem(sys.modules, "yaml", yaml_mod)

        p = Plugin.from_directory(root)
        assert p.name == "yaml-plugin"
        assert p.version == "2.0.0"

    def test_command_without_description_line(self, tmp_path: Path) -> None:
        root = tmp_path / "cmd-test"
        root.mkdir()
        cmds = root / "commands"
        cmds.mkdir()
        (cmds / "noop.md").write_text("just a prompt", encoding="utf-8")
        p = Plugin.from_directory(root)
        assert p.commands[0].name == "noop"
        # When there's no # heading, description falls back to first line content
        assert p.commands[0].description == "just a prompt"
        assert p.commands[0].prompt == "just a prompt"


class TestPluginMergeInto:
    def test_extends_spec(self, plugin_dir: Path) -> None:
        p = Plugin.from_directory(plugin_dir)
        spec = HarnessSpec.default()
        original_commands = len(spec.commands)
        original_rules = len(spec.rules)
        original_hooks = len(spec.hooks)

        merged = p.merge_into(spec)
        assert merged is spec  # same object, mutated
        assert len(spec.commands) == original_commands + 1
        assert len(spec.rules) == original_rules + 1
        assert len(spec.hooks) == original_hooks + 1
        assert "my-server" in spec.mcp_servers
        assert "Use black." in spec.research_protocol

    def test_merge_without_conventions(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        p = Plugin.from_directory(root)
        spec = HarnessSpec(research_protocol="base")
        p.merge_into(spec)
        assert spec.research_protocol == "base"


class TestPluginManager:
    def test_creates_plugins_dir(self, tmp_path: Path) -> None:
        _ = PluginManager(tmp_path)
        assert (tmp_path / ".maru" / "plugins").exists()

    def test_list_plugins_empty(self, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        assert mgr.list_plugins() == []

    def test_list_plugins_loads_installed(self, plugin_dir: Path, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        target = mgr.plugins_dir / "my-plugin"
        target.mkdir(parents=True)
        for f in plugin_dir.iterdir():
            if f.is_dir():
                (target / f.name).mkdir()
                for child in f.iterdir():
                    (target / f.name / child.name).write_text(child.read_text(), encoding="utf-8")
            else:
                (target / f.name).write_text(f.read_text(), encoding="utf-8")
        plugins = mgr.list_plugins()
        assert len(plugins) == 1
        assert plugins[0].name == "my-plugin"

    def test_list_plugins_skips_broken(self, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        bad = mgr.plugins_dir / "bad"
        bad.mkdir()
        (bad / "plugin.json").write_text("not json", encoding="utf-8")
        plugins = mgr.list_plugins()
        assert plugins == []

    def test_install_local_directory(self, plugin_dir: Path, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        p = mgr.install(str(plugin_dir))
        assert p.name == "my-plugin"
        assert (mgr.plugins_dir / "my-plugin" / "plugin.json").exists()

    def test_install_local_file_copies(self, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        src = tmp_path / "some.txt"
        src.write_text("hello", encoding="utf-8")
        p = mgr.install(str(src))
        assert p.name == "some.txt"
        assert (mgr.plugins_dir / "some.txt" / "some.txt").read_text() == "hello"

    def test_install_raises_when_missing(self, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.install(str(tmp_path / "nope"))

    def test_uninstall_existing(self, plugin_dir: Path, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        mgr.install(str(plugin_dir))
        assert (mgr.plugins_dir / "my-plugin").exists()
        assert mgr.uninstall("my-plugin") is True
        assert not (mgr.plugins_dir / "my-plugin").exists()

    def test_uninstall_missing(self, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        assert mgr.uninstall("nope") is False

    @patch("subprocess.run")
    def test_install_git(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        # Pre-create the target dir as if git clone succeeded
        target = mgr.plugins_dir / "my-plugin"
        target.mkdir(parents=True)
        (target / "plugin.json").write_text(
            json.dumps({"name": "my-plugin", "version": "1.0.0", "agents": []}),
            encoding="utf-8",
        )
        p = mgr.install("https://github.com/user/maru-plugin-my-plugin.git")
        assert p.name == "my-plugin"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "git"
        assert args[1] == "clone"

    def test_get_merged_spec_default_base(self, plugin_dir: Path, tmp_path: Path) -> None:
        mgr = PluginManager(tmp_path)
        mgr.install(str(plugin_dir))
        spec = mgr.get_merged_spec()
        assert isinstance(spec, HarnessSpec)
        assert any(c.name == "research" for c in spec.commands)
