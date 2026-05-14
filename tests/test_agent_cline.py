"""Tests for Cline agent adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from maru_deep_pro_search.cli.agents.cline import ClineAdapter


class TestDetect:
    def test_detected_via_vscode_ext(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        (tmp_path / ".vscode" / "extensions" / "saoudrizwan.claude-dev").mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ClineAdapter().detect() is True

    def test_detected_via_binary(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/cline" if cmd == "cline" else None
        )
        assert ClineAdapter().detect() is True

    def test_not_detected(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert ClineAdapter().detect() is False


class TestPaths:
    def test_rules_dir_user_with_documents(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "Documents").mkdir()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        p = ClineAdapter()._rules_dir("user")
        assert "Documents" in str(p)

    def test_rules_dir_user_no_documents(self, monkeypatch: Any, tmp_path: Path) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        p = ClineAdapter()._rules_dir("user")
        assert "Cline" in str(p)

    def test_rules_dir_project(self) -> None:
        p = ClineAdapter()._rules_dir("project")
        assert p == Path(".clinerules")

    def test_hooks_dir_user(self) -> None:
        p = ClineAdapter()._hooks_dir("user")
        assert ".cline" in str(p)

    def test_hooks_dir_project(self) -> None:
        p = ClineAdapter()._hooks_dir("project")
        assert p == Path(".cline") / "hooks"

    def test_agents_dir_user(self) -> None:
        p = ClineAdapter()._agents_dir("user")
        assert ".cline" in str(p)

    def test_agents_dir_project(self) -> None:
        p = ClineAdapter()._agents_dir("project")
        assert p == Path(".cline") / "agents"

    def test_skills_dir_user(self) -> None:
        p = ClineAdapter()._skills_dir("user")
        assert p is not None
        assert ".cline" in str(p)

    def test_skills_dir_project(self) -> None:
        p = ClineAdapter()._skills_dir("project")
        assert p is not None
        assert p == Path(".cline") / "skills"

    def test_cron_dir_user(self) -> None:
        p = ClineAdapter()._cron_dir("user")
        assert ".cline" in str(p)

    def test_cron_dir_project(self) -> None:
        p = ClineAdapter()._cron_dir("project")
        assert p == Path(".cline") / "cron"

    def test_mcp_path_user(self) -> None:
        p = ClineAdapter()._mcp_path("user")
        assert p.name == "mcp.json"

    def test_mcp_path_project(self) -> None:
        p = ClineAdapter()._mcp_path("project")
        assert p == Path(".cline", "mcp.json")


class TestBackupRestore:
    def test_backup_with_files_and_dirs(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        mcp = tmp_path / ".cline" / "mcp.json"
        mcp.parent.mkdir(parents=True)
        mcp.touch()
        hooks = tmp_path / ".cline" / "hooks"
        hooks.mkdir()
        (hooks / "PreToolUse.py").touch()
        rules = tmp_path / "Documents" / "Cline" / "Rules"
        rules.mkdir(parents=True)

        file_baks: list[Path] = []
        dir_baks: list[Path] = []

        def _bf(p: Path) -> Path:
            file_baks.append(p)
            return tmp_path / f"{p.name}.bak.0"

        def _bd(p: Path) -> Path:
            dir_baks.append(p)
            return tmp_path / f"{p.name}.bak.0"

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.cline.backup_file", _bf)
        monkeypatch.setattr("maru_deep_pro_search.cli.agents.cline.backup_dir", _bd)

        backups = adapter.backup()
        assert len(backups) == 3
        assert len(file_baks) == 2
        assert len(dir_baks) == 1

    def test_backup_skips_missing(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.backup_file",
            lambda _p: tmp_path / "bak",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.backup_dir",
            lambda _p: tmp_path / "bak",
        )
        assert adapter.backup() == []

    def test_restore_no_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert adapter.restore() is False

    def test_restore_with_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        mcp = tmp_path / ".cline" / "mcp.json"
        mcp.parent.mkdir(parents=True)
        mcp.touch()
        (mcp.parent / "mcp.json.bak.0").touch()
        hooks = tmp_path / ".cline" / "hooks"
        hooks.mkdir()
        ptu = hooks / "PreToolUse.py"
        ptu.touch()
        (hooks / "PreToolUse.py.bak.0").touch()
        rules = tmp_path / "Documents" / "Cline" / "Rules"
        rules.mkdir(parents=True)
        (rules.parent / "Rules.bak.0").mkdir()

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.restore_file",
            lambda _orig, _bak: True,
        )
        restored_dirs: list[tuple] = []

        def _rd(orig: Path, bak: Path) -> bool:
            restored_dirs.append((orig, bak))
            return True

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.restore_dir",
            _rd,
        )
        assert adapter.restore() is True
        assert len(restored_dirs) == 1


class TestInstallMcp:
    def test_install_mcp_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(adapter, "_mcp_path", lambda _s: tmp_path / "mcp.json")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.backup.read_json_safe",
            lambda _p: {},
        )
        written: dict[str, Any] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.backup.write_json_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.get_mcp_server_command",
            lambda: {"command": "python", "args": ["-m", "maru"]},
        )
        assert adapter.install_mcp("user") is True
        cfg = written[str(tmp_path / "mcp.json")]
        assert "maru-deep-pro-search" in cfg["mcpServers"]


class TestInjectRules:
    def test_inject_rules_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.read_text_safe",
            lambda _p: "",
        )
        written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.write_text_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        assert adapter.inject_rules("user") is True
        assert any("maru-research-protocol.md" in k for k in written)
        # Hook, agent, cron files use Path.write_text directly
        assert (tmp_path / ".cline" / "hooks" / "PreToolUse.py").exists()
        assert (tmp_path / ".cline" / "agents" / "maru-research-gate.md").exists()
        assert (tmp_path / ".cline" / "cron" / "maru-research-check.cron.md").exists()

    def test_inject_rules_idempotent(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.read_text_safe",
            lambda _p: "# PROTOCOL\n",
        )
        written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.write_text_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.inject_protocol",
            lambda content, _protocol: content,
        )
        assert adapter.inject_rules("user") is True
        assert len(written) == 0

    def test_inject_rules_skips_existing_files(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = ClineAdapter()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        hooks = tmp_path / ".cline" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "PreToolUse.py").touch()
        agents = tmp_path / ".cline" / "agents"
        agents.mkdir(parents=True)
        (agents / "maru-research-gate.md").touch()
        cron = tmp_path / ".cline" / "cron"
        cron.mkdir(parents=True)
        (cron / "maru-research-check.cron.md").touch()

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.read_text_safe",
            lambda _p: "",
        )
        written: dict[str, str] = {}
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.write_text_safe",
            lambda p, data: written.update({str(p): data}),
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.cline.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        assert adapter.inject_rules("user") is True
        # Only rules file should be written
        assert len(written) == 1
        assert "maru-research-protocol.md" in list(written.keys())[0]
