"""Tests for remaining CLI command modules."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

# ═══════════════════════════════════════════════════════════════
# init_cmd
# ═══════════════════════════════════════════════════════════════


class TestInitCmd:
    def test_init_defaults(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.init_cmd import main

        called = {}
        def _fake_init(*, path, agents, create_agents_md, create_gitignore):
            called.update(
                {"path": path, "agents": agents, "agents_md": create_agents_md, "gitignore": create_gitignore}
            )
            return {"created": [".maru"], "root": "/tmp/test"}

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.init_cmd.init_project", _fake_init
        )
        assert main([]) == 0
        captured = capsys.readouterr()
        assert "Harness initialized" in captured.out
        assert called["agents_md"] is True
        assert called["gitignore"] is True

    def test_init_with_agents(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.init_cmd import main

        def _fake_init(*, path, agents, create_agents_md, create_gitignore):
            return {"created": [".maru"], "root": "/tmp/test"}

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.init_cmd.init_project", _fake_init
        )
        assert main(["--agents", "claude", "cursor"]) == 0
        captured = capsys.readouterr()
        assert "Agents configured" in captured.out

    def test_init_skips_agents_md(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.init_cmd import main

        called = {}
        def _fake_init(*, path, agents, create_agents_md, create_gitignore):
            called["agents_md"] = create_agents_md
            return {"created": [".maru"], "root": "/tmp/test"}

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.init_cmd.init_project", _fake_init
        )
        assert main(["--no-agents-md"]) == 0
        assert called["agents_md"] is False


# ═══════════════════════════════════════════════════════════════
# plugin_cmd
# ═══════════════════════════════════════════════════════════════


class TestPluginCmd:
    def test_list_empty(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.plugin_cmd import main

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.plugin_cmd.PluginManager",
            lambda path: MagicMock(list_plugins=lambda: []),
        )
        assert main(["list"]) == 0
        captured = capsys.readouterr()
        assert "플러그인이 없습니다" in captured.out

    def test_list_with_plugins(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.plugin_cmd import main

        p = MagicMock()
        p.name = "test-plugin"
        p.version = "1.0.0"
        p.description = "A test plugin"
        p.agents = ["claude"]
        p.commands = []
        p.rules = []
        p.hooks = []
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.plugin_cmd.PluginManager",
            lambda path: MagicMock(list_plugins=lambda: [p]),
        )
        assert main(["list"]) == 0
        captured = capsys.readouterr()
        assert "test-plugin" in captured.out

    def test_install_success(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.plugin_cmd import main

        p = MagicMock()
        p.name = "my-plugin"
        p.version = "1.0.0"
        p.commands = []
        p.hooks = []
        mgr = MagicMock()
        mgr.install.return_value = p
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.plugin_cmd.PluginManager",
            lambda path: mgr,
        )
        assert main(["install", "./my-plugin"]) == 0
        captured = capsys.readouterr()
        assert "my-plugin" in captured.out
        mgr.install.assert_called_once_with("./my-plugin")

    def test_install_failure(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.plugin_cmd import main

        mgr = MagicMock()
        mgr.install.side_effect = RuntimeError("bad plugin")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.plugin_cmd.PluginManager",
            lambda path: mgr,
        )
        assert main(["install", "./bad"]) == 1
        captured = capsys.readouterr()
        assert "설치 실패" in captured.out

    def test_uninstall_success(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.plugin_cmd import main

        mgr = MagicMock()
        mgr.uninstall.return_value = True
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.plugin_cmd.PluginManager",
            lambda path: mgr,
        )
        assert main(["uninstall", "my-plugin"]) == 0
        mgr.uninstall.assert_called_once_with("my-plugin")

    def test_uninstall_not_found(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.plugin_cmd import main

        mgr = MagicMock()
        mgr.uninstall.return_value = False
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.plugin_cmd.PluginManager",
            lambda path: mgr,
        )
        assert main(["uninstall", "missing"]) == 1

    def test_no_command_prints_help(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.plugin_cmd import main

        assert main([]) == 0
        captured = capsys.readouterr()
        assert "plugin" in captured.out.lower()


# ═══════════════════════════════════════════════════════════════
# stats_cmd
# ═══════════════════════════════════════════════════════════════


class TestStatsCmd:
    def test_stats_success(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.stats_cmd import main

        class MockStore:
            def __init__(self, path: str) -> None:
                self.path = path
            def get_stats(self):
                return {
                    "total_entries": 42,
                    "last_7_days": 7,
                    "top_queries": [("python asyncio", 5)],
                }
            @classmethod
            def _default_db_path(cls) -> str:
                return "/tmp/knowledge.db"
            def _connect(self):
                return MagicMock()

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.stats_cmd.KnowledgeStore",
            MockStore,
        )
        assert main([]) == 0
        captured = capsys.readouterr()
        assert "42" in captured.out
        assert "python asyncio" in captured.out

    def test_stats_error(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.stats_cmd import main

        class MockStore:
            def __init__(self, path: str) -> None:
                self.path = path
            def get_stats(self):
                raise RuntimeError("db locked")
            @classmethod
            def _default_db_path(cls) -> str:
                return "/tmp/knowledge.db"

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.stats_cmd.KnowledgeStore",
            MockStore,
        )
        assert main([]) == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ═══════════════════════════════════════════════════════════════
# update_cmd
# ═══════════════════════════════════════════════════════════════


class TestUpdateCmd:
    def test_up_to_date(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.update_cmd import main

        result = MagicMock()
        result.error = None
        result.current_version = "0.11.3"
        result.latest_version = "0.11.3"
        result.update_available = False
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.update_cmd.check_for_update",
            lambda: result,
        )
        assert main([]) == 0
        captured = capsys.readouterr()
        assert "latest version" in captured.out.lower() or "최신" in captured.out

    def test_update_available_check_only(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.update_cmd import main

        result = MagicMock()
        result.error = None
        result.current_version = "0.11.0"
        result.latest_version = "0.11.3"
        result.update_available = True
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.update_cmd.check_for_update",
            lambda: result,
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.update_cmd.get_update_notice",
            lambda r: "",
        )
        assert main(["--check"]) == 0
        captured = capsys.readouterr()
        assert "0.11.3" in captured.out

    def test_update_error(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.update_cmd import main

        result = MagicMock()
        result.error = "network timeout"
        result.current_version = "0.11.0"
        result.latest_version = None
        result.update_available = False
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.update_cmd.check_for_update",
            lambda: result,
        )
        assert main([]) == 1
        captured = capsys.readouterr()
        assert "network timeout" in captured.out

    def test_update_performs(self, monkeypatch: Any, capsys: Any) -> None:
        from maru_deep_pro_search.cli.update_cmd import main

        result = MagicMock()
        result.error = None
        result.current_version = "0.11.0"
        result.latest_version = "0.11.3"
        result.update_available = True
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.update_cmd.check_for_update",
            lambda: result,
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.update_cmd.get_update_notice",
            lambda r: "",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.update_cmd.perform_update",
            lambda dry_run: (True, "updated"),
        )
        assert main([]) == 0
        captured = capsys.readouterr()
        assert "updated" in captured.out
