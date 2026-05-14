"""Tests for Zed agent adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from maru_deep_pro_search.cli.agents.zed import ZedAdapter


class TestDetect:
    def test_detected_via_binary(self, monkeypatch: Any) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/zed" if cmd == "zed" else None)
        assert ZedAdapter().detect() is True

    def test_detected_via_config_dir(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".config" / "zed").mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ZedAdapter().detect() is True

    def test_detected_via_zed_dir(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".zed").mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ZedAdapter().detect() is True

    def test_not_detected(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ZedAdapter().detect() is False


class TestPaths:
    def test_settings_user(self) -> None:
        p = ZedAdapter()._settings_path("user")
        assert p.name == "settings.json"

    def test_settings_project(self) -> None:
        p = ZedAdapter()._settings_path("project")
        assert p == Path(".zed") / "settings.json"

    def test_assistant_user(self) -> None:
        p = ZedAdapter()._assistant_path("user")
        assert p.name == "assistant.md"

    def test_assistant_project(self) -> None:
        p = ZedAdapter()._assistant_path("project")
        assert p == Path(".zed") / "assistant.md"

    def test_rules_project(self) -> None:
        p = ZedAdapter()._rules_path("project")
        assert p == Path(".rules")

    def test_rules_user(self) -> None:
        p = ZedAdapter()._rules_path("user")
        assert "rules" in str(p)


class TestBackupRestore:
    def test_backup(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(adapter, "_assistant_path", lambda _s: tmp_path / "assistant.md")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.backup_file",
            lambda p: tmp_path / f"{p.name}.bak.0",
        )
        backups = adapter.backup()
        assert len(backups) == 2

    def test_backup_skips_none(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(adapter, "_assistant_path", lambda _s: tmp_path / "assistant.md")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.backup_file",
            lambda _p: None,
        )
        assert adapter.backup() == []

    def test_restore_no_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(adapter, "_assistant_path", lambda _s: tmp_path / "assistant.md")
        assert adapter.restore() is False

    def test_restore_with_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        settings = tmp_path / "settings.json"
        settings.touch()
        (tmp_path / "settings.json.bak.0").touch()
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: settings)
        monkeypatch.setattr(adapter, "_assistant_path", lambda _s: tmp_path / "assistant.md")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.restore_file",
            lambda _orig, _bak: True,
        )
        assert adapter.restore() is True


class TestInstallMcp:
    def test_install_mcp_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_json_safe",
            lambda _p: {},
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.get_mcp_server_command_list",
            lambda: ["python", "-m", "maru_deep_pro_search"],
        )
        assert adapter.install_mcp("user") is True
        cfg = written[str(tmp_path / "settings.json")]
        assert "context_servers" in cfg
        assert cfg["context_servers"]["maru-deep-pro-search"]["command"] == "python"
        assert cfg["agent"]["tool_permissions"]["default"] == "allow"

    def test_install_mcp_existing_config(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_json_safe",
            lambda _p: {
                "context_servers": {"other": {}},
                "agent": {"tool_permissions": {"default": "deny"}},
            },
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.get_mcp_server_command_list",
            lambda: ["cmd"],
        )
        assert adapter.install_mcp("user") is True
        cfg = written[str(tmp_path / "settings.json")]
        assert "other" in cfg["context_servers"]
        assert "maru-deep-pro-search" in cfg["context_servers"]


class TestInjectRules:
    def test_inject_rules_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_assistant_path", lambda _s: tmp_path / "assistant.md")
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(adapter, "_rules_path", lambda _s: tmp_path / ".rules")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_text_safe",
            lambda _p: "",
        )
        written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_text_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_json_safe",
            lambda _p: {},
        )
        cfg_written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_json_safe",
            lambda p, data: cfg_written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        assert adapter.inject_rules("user") is True
        assert str(tmp_path / "assistant.md") in written
        assert str(tmp_path / ".rules") not in written
        cfg = cfg_written[str(tmp_path / "settings.json")]
        assert "deep_research" in cfg["assistant"]["default_instructions"]
        assert cfg["assistant"]["default_model"]["model"] == "claude-sonnet-4-5"

    def test_inject_rules_project(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_assistant_path", lambda _s: tmp_path / "assistant.md")
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(adapter, "_rules_path", lambda _s: tmp_path / ".rules")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_text_safe",
            lambda _p: "",
        )
        written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_text_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_json_safe",
            lambda _p: {},
        )
        cfg_written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_json_safe",
            lambda p, data: cfg_written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        assert adapter.inject_rules("project") is True
        assert str(tmp_path / ".rules") in written

    def test_inject_rules_idempotent(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ZedAdapter()
        monkeypatch.setattr(adapter, "_assistant_path", lambda _s: tmp_path / "assistant.md")
        monkeypatch.setattr(adapter, "_settings_path", lambda _s: tmp_path / "settings.json")
        monkeypatch.setattr(adapter, "_rules_path", lambda _s: tmp_path / ".rules")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_text_safe",
            lambda _p: "# PROTOCOL\n",
        )
        written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_text_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.read_json_safe",
            lambda _p: {
                "assistant": {
                    "default_instructions": "already set",
                    "default_model": {"provider": "custom", "model": "gpt-4"},
                }
            },
        )
        cfg_written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.write_json_safe",
            lambda p, data: cfg_written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.zed.inject_protocol",
            lambda content, _protocol: content,
        )
        assert adapter.inject_rules("user") is True
        assert str(tmp_path / "assistant.md") not in written
        cfg = cfg_written[str(tmp_path / "settings.json")]
        assert cfg["assistant"]["default_model"]["model"] == "gpt-4"
