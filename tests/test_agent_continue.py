"""Tests for Continue agent adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from maru_deep_pro_search.cli.agents.continue_ import ContinueAdapter


class TestDetect:
    def test_detected_via_binary(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/continue" if cmd == "continue" else None
        )
        assert ContinueAdapter().detect() is True

    def test_detected_via_config_yaml(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".continue" / "config.yaml").mkdir(parents=True)
        (tmp_path / ".continue" / "config.yaml").touch()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ContinueAdapter().detect() is True

    def test_detected_via_config_json(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".continue" / "config.json").mkdir(parents=True)
        (tmp_path / ".continue" / "config.json").touch()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ContinueAdapter().detect() is True

    def test_detected_via_xdg_config(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".config" / "continue" / "config.json").mkdir(parents=True)
        (tmp_path / ".config" / "continue" / "config.json").touch()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ContinueAdapter().detect() is True

    def test_not_detected(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ContinueAdapter().detect() is False


class TestPaths:
    def test_config_user(self) -> None:
        p = ContinueAdapter()._config_path("user")
        assert p.name == "config.json"
        assert ".continue" in str(p)

    def test_config_project(self) -> None:
        p = ContinueAdapter()._config_path("project")
        assert p == Path(".continue", "config.json")

    def test_ignore_user(self) -> None:
        p = ContinueAdapter()._ignore_path("user")
        assert p.name == ".continueignore"

    def test_ignore_project(self) -> None:
        p = ContinueAdapter()._ignore_path("project")
        assert p == Path(".continueignore")

    def test_skills_dir_user(self) -> None:
        p = ContinueAdapter()._skills_dir("user")
        assert p is not None
        assert "rules" in str(p)

    def test_skills_dir_project(self) -> None:
        p = ContinueAdapter()._skills_dir("project")
        assert p is not None
        assert p == Path(".continue") / "rules"


class TestBackupRestore:
    def test_backup(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.backup_file",
            lambda _p: tmp_path / "config.json.bak.0",
        )
        assert len(adapter.backup()) == 1

    def test_backup_none(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.backup_file",
            lambda _p: None,
        )
        assert adapter.backup() == []

    def test_restore_no_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        assert adapter.restore() is False

    def test_restore_with_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        cfg = tmp_path / "config.json"
        cfg.touch()
        (tmp_path / "config.json.bak.0").touch()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: cfg)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.restore_file",
            lambda _orig, _bak: True,
        )
        assert adapter.restore() is True


class TestInstallMcp:
    def test_install_mcp_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.read_json_safe",
            lambda _p: {},
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.get_mcp_server_command",
            lambda: {"command": "python", "args": ["-m", "maru"]},
        )
        assert adapter.install_mcp("user") is True
        cfg = written[str(tmp_path / "config.json")]
        assert "maru-deep-pro-search" in cfg["server"]["mcpServers"]

    def test_install_mcp_existing(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.read_json_safe",
            lambda _p: {"server": {"mcpServers": {"other": {}}}},
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.get_mcp_server_command",
            lambda: {"command": "python"},
        )
        assert adapter.install_mcp("user") is True
        cfg = written[str(tmp_path / "config.json")]
        assert "other" in cfg["server"]["mcpServers"]


class TestInjectRules:
    def test_inject_rules_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / ".continueignore")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.read_json_safe",
            lambda _p: {},
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        assert adapter.inject_rules("user") is True
        cfg = written[str(tmp_path / "config.json")]
        names = [c["name"] for c in cfg["custom_commands"]]
        assert "research" in names
        assert "verify" in names
        assert cfg["system_message"] == "# PROTOCOL\n"
        assert (tmp_path / ".continueignore").exists()

    def test_inject_rules_idempotent(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / ".continueignore")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.read_json_safe",
            lambda _p: {
                "custom_commands": [
                    {"name": "research"},
                    {"name": "verify"},
                ],
                "system_message": "# PROTOCOL\n",
            },
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.inject_protocol",
            lambda content, _protocol: content,
        )
        assert adapter.inject_rules("user") is True
        cfg = written[str(tmp_path / "config.json")]
        assert len(cfg["custom_commands"]) == 2
        # system_message unchanged because inject_protocol returned same content
        assert cfg.get("system_message") == "# PROTOCOL\n"

    def test_inject_rules_ignore_exists(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ContinueAdapter()
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "config.json")
        ignore = tmp_path / ".continueignore"
        ignore.write_text("existing\n")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: ignore)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.read_json_safe",
            lambda _p: {},
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.continue_.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        assert adapter.inject_rules("user") is True
        assert "existing" in ignore.read_text()
