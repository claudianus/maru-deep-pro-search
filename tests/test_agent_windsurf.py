"""Tests for Windsurf agent adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from maru_deep_pro_search.cli.agents.windsurf import WindsurfAdapter


class TestDetect:
    def test_detected_via_project_dir(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".windsurf").mkdir()
        monkeypatch.chdir(tmp_path)
        assert WindsurfAdapter().detect() is True

    def test_detected_via_home_dir(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".windsurf").mkdir()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert WindsurfAdapter().detect() is True

    def test_detected_via_binary(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/windsurf" if cmd == "windsurf" else None
        )
        assert WindsurfAdapter().detect() is True

    def test_not_detected(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert WindsurfAdapter().detect() is False


class TestPaths:
    def test_mcp_user(self) -> None:
        p = WindsurfAdapter()._mcp_path("user")
        assert p.name == "mcp_config.json"

    def test_mcp_project(self) -> None:
        p = WindsurfAdapter()._mcp_path("project")
        assert p == Path(".codeium") / "windsurf" / "mcp_config.json"

    def test_hooks_user(self) -> None:
        p = WindsurfAdapter()._hooks_path("user")
        assert p.name == "hooks.json"

    def test_hooks_project(self) -> None:
        p = WindsurfAdapter()._hooks_path("project")
        assert p == Path(".windsurf") / "hooks.json"

    def test_rules_dir_user(self) -> None:
        p = WindsurfAdapter()._rules_dir("user")
        assert p.name == "rules"

    def test_rules_dir_project(self) -> None:
        p = WindsurfAdapter()._rules_dir("project")
        assert p == Path(".windsurf") / "rules"

    def test_agents_md_user(self) -> None:
        p = WindsurfAdapter()._agents_md_path("user")
        assert p.name == "AGENTS.md"

    def test_agents_md_project(self) -> None:
        p = WindsurfAdapter()._agents_md_path("project")
        assert p == Path("AGENTS.md")

    def test_skills_dir_user(self) -> None:
        p = WindsurfAdapter()._skills_dir("user")
        assert p is not None
        assert p.name == "rules"

    def test_skills_dir_project(self) -> None:
        p = WindsurfAdapter()._skills_dir("project")
        assert p is not None
        assert p == Path(".windsurf") / "rules"


class TestBackupRestore:
    def test_backup_files_and_dirs(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        monkeypatch.setattr(adapter, "_mcp_path", lambda _s: tmp_path / "mcp.json")
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: tmp_path / "hooks.json")
        monkeypatch.setattr(adapter, "_agents_md_path", lambda _s: tmp_path / "AGENTS.md")
        monkeypatch.setattr(adapter, "_rules_dir", lambda _s: tmp_path / "rules")

        (tmp_path / "mcp.json").touch()
        (tmp_path / "hooks.json").touch()
        (tmp_path / "AGENTS.md").touch()
        (tmp_path / "rules").mkdir()

        file_backups: list[Path] = []
        dir_backups: list[Path] = []

        def _backup_file(p: Path) -> Path:
            file_backups.append(p)
            return tmp_path / f"{p.name}.bak.0"

        def _backup_dir(p: Path) -> Path:
            dir_backups.append(p)
            return tmp_path / f"{p.name}.bak.0"

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.backup_file",
            _backup_file,
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.backup_dir",
            _backup_dir,
        )

        backups = adapter.backup()
        assert len(backups) == 4
        assert len(file_backups) == 3
        assert len(dir_backups) == 1

    def test_backup_skips_missing(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        monkeypatch.setattr(adapter, "_mcp_path", lambda _s: tmp_path / "mcp.json")
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: tmp_path / "hooks.json")
        monkeypatch.setattr(adapter, "_agents_md_path", lambda _s: tmp_path / "AGENTS.md")
        monkeypatch.setattr(adapter, "_rules_dir", lambda _s: tmp_path / "rules")

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.backup_file",
            lambda _p: tmp_path / "bak",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.backup_dir",
            lambda _p: tmp_path / "bak",
        )

        assert adapter.backup() == []

    def test_restore_no_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        monkeypatch.setattr(adapter, "_mcp_path", lambda _s: tmp_path / "mcp.json")
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: tmp_path / "hooks.json")
        monkeypatch.setattr(adapter, "_agents_md_path", lambda _s: tmp_path / "AGENTS.md")
        monkeypatch.setattr(adapter, "_rules_dir", lambda _s: tmp_path / "rules")
        assert adapter.restore() is False

    def test_restore_with_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        mcp = tmp_path / "mcp.json"
        mcp.touch()
        (tmp_path / "mcp.json.bak.0").touch()
        monkeypatch.setattr(adapter, "_mcp_path", lambda _s: mcp)
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: tmp_path / "hooks.json")
        monkeypatch.setattr(adapter, "_agents_md_path", lambda _s: tmp_path / "AGENTS.md")
        monkeypatch.setattr(adapter, "_rules_dir", lambda _s: tmp_path / "rules")

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.restore_file",
            lambda _orig, _bak: True,
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.restore_dir",
            lambda _orig, _bak: True,
        )
        assert adapter.restore() is True


class TestInstallMcp:
    def test_install_mcp_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        monkeypatch.setattr(adapter, "_mcp_path", lambda _s: tmp_path / "mcp.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.read_json_safe",
            lambda _p: {},
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.get_mcp_server_command",
            lambda: {"command": "python", "args": ["-m", "maru"]},
        )
        assert adapter.install_mcp("user") is True
        cfg = written[str(tmp_path / "mcp.json")]
        assert "maru-deep-pro-search" in cfg["mcpServers"]


class TestInjectRules:
    def test_inject_rules_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        monkeypatch.setattr(adapter, "_rules_dir", lambda _s: tmp_path / "rules")
        monkeypatch.setattr(adapter, "_agents_md_path", lambda _s: tmp_path / "AGENTS.md")
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: tmp_path / "hooks.json")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.read_text_safe",
            lambda _p: "",
        )
        text_written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.write_text_safe",
            lambda p, data: text_written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.read_json_safe",
            lambda _p: {},
        )
        json_written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.write_json_safe",
            lambda p, data: json_written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        assert adapter.inject_rules("user") is True
        assert any("maru-research-protocol.md" in k for k in text_written)
        assert str(tmp_path / "AGENTS.md") in text_written
        hooks = json_written[str(tmp_path / "hooks.json")]
        assert "pre_write_code" in hooks
        assert "pre_mcp_tool_use" in hooks

    def test_inject_rules_idempotent(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        monkeypatch.setattr(adapter, "_rules_dir", lambda _s: tmp_path / "rules")
        monkeypatch.setattr(adapter, "_agents_md_path", lambda _s: tmp_path / "AGENTS.md")
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: tmp_path / "hooks.json")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.read_text_safe",
            lambda _p: "# PROTOCOL\n",
        )
        text_written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.write_text_safe",
            lambda p, data: text_written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.read_json_safe",
            lambda _p: {
                "pre_write_code": [{"command": "existing", "show_output": True}],
            },
        )
        json_written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.write_json_safe",
            lambda p, data: json_written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.inject_protocol",
            lambda content, _protocol: content,
        )
        assert adapter.inject_rules("user") is True
        assert str(tmp_path / "AGENTS.md") not in text_written
        hooks = json_written[str(tmp_path / "hooks.json")]
        assert hooks["pre_write_code"][0]["command"] == "existing"

    def test_install_hooks_array_backup(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        hooks_path = tmp_path / "hooks.json"
        hooks_path.write_text("[]")
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: hooks_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.read_json_safe",
            lambda _p: [],
        )
        json_written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.write_json_safe",
            lambda p, data: json_written.update({str(p): data}),
        )
        backup_called = [False]
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.backup_file",
            lambda _p: backup_called.__setitem__(0, True),
        )
        adapter._install_hooks("user")
        assert backup_called[0]
        hooks = json_written[str(hooks_path)]
        assert isinstance(hooks, dict)
        assert "pre_write_code" in hooks

    def test_install_hooks_invalid_json(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        hooks_path = tmp_path / "hooks.json"
        hooks_path.write_text("not json")
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: hooks_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.read_json_safe",
            lambda _p: {},
        )
        json_written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.write_json_safe",
            lambda p, data: json_written.update({str(p): data}),
        )
        adapter._install_hooks("user")
        hooks = json_written[str(hooks_path)]
        assert "pre_write_code" in hooks

    def test_restore_with_dir_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = WindsurfAdapter()
        mcp = tmp_path / "mcp.json"
        mcp.touch()
        rules = tmp_path / "rules"
        rules.mkdir()
        (tmp_path / "rules.bak.0").mkdir()
        monkeypatch.setattr(adapter, "_mcp_path", lambda _s: mcp)
        monkeypatch.setattr(adapter, "_hooks_path", lambda _s: tmp_path / "hooks.json")
        monkeypatch.setattr(adapter, "_agents_md_path", lambda _s: tmp_path / "AGENTS.md")
        monkeypatch.setattr(adapter, "_rules_dir", lambda _s: rules)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.restore_file",
            lambda _orig, _bak: True,
        )
        restored_dirs: list[tuple] = []

        def _restore_dir(orig: Path, bak: Path) -> bool:
            restored_dirs.append((orig, bak))
            return True

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.windsurf.restore_dir",
            _restore_dir,
        )
        assert adapter.restore() is True
        assert len(restored_dirs) == 1
