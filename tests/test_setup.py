"""Tests for the setup CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from maru_deep_pro_search.cli.setup import (
    ADAPTER_REGISTRY,
    cmd_check,
    cmd_list,
    cmd_restore,
    cmd_setup,
    main,
)


@pytest.fixture(autouse=True)
def _mock_python_compat(monkeypatch: Any) -> None:
    """Always pass Python version check."""
    monkeypatch.setattr(
        "maru_deep_pro_search.cli.setup.ensure_compatible_python",
        lambda: 0,
    )


@pytest.fixture
def mock_adapter(monkeypatch: Any) -> MagicMock:
    """Return a reusable mock adapter class."""
    cls = MagicMock()
    inst = cls.return_value
    inst.display_name = "MockAgent"
    inst.configure.return_value = {
        "backups": [],
        "mcp_installed": True,
        "rules_injected": True,
    }
    inst.detect.return_value = True
    inst.restore.return_value = True
    inst.install_mcp.return_value = True
    monkeypatch.setitem(ADAPTER_REGISTRY, "mock", cls)
    return cls


class TestCmdList:
    def test_lists_detected_and_missing(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"claude": True, "cursor": False},
        )
        args = MagicMock()
        assert cmd_list(args) == 0
        captured = capsys.readouterr()
        assert "Claude" in captured.out
        assert "Cursor" in captured.out


class TestCmdSetup:
    def test_no_agents_found(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"claude": False},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 1
        captured = capsys.readouterr()
        assert "찾을 수 없습니다" in captured.out

    def test_selected_not_installed(self, monkeypatch: Any, capsys: Any) -> None:
        # No agents installed at all → hits line 85-89
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"claude": False},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 1
        captured = capsys.readouterr()
        assert "찾을 수 없습니다" in captured.out

    def test_selected_agents_not_in_installed(self, monkeypatch: Any, capsys: Any) -> None:
        # Agents are installed but selected ones are not → hits line 97-98
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"claude": True, "cursor": False},
        )
        args = MagicMock()
        args.agents = ["cursor"]
        args.scope = "user"
        assert cmd_setup(args) == 1
        captured = capsys.readouterr()
        assert "선택한 에이전트 중 설치된 것이 없습니다" in captured.out

    def test_setup_success(self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "완료" in captured.out
        mock_adapter.return_value.configure.assert_called_once_with(scope="user")

    def test_setup_with_skills(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        mock_adapter.return_value.configure.return_value = {
            "backups": [Path("/tmp/bak")],
            "mcp_installed": True,
            "rules_injected": True,
            "skills_installed": True,
            "skills_supported": True,
        }
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "SKILL.md" in captured.out

    def test_setup_mcp_failure(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        mock_adapter.return_value.configure.return_value = {
            "backups": [],
            "mcp_installed": False,
            "rules_injected": True,
        }
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "MCP 서버 등록 실패" in captured.out

    def test_setup_rules_failure(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        mock_adapter.return_value.configure.return_value = {
            "backups": [],
            "mcp_installed": True,
            "rules_injected": False,
        }
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "규칙 주입 실패" in captured.out

    def test_setup_skills_failure(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        mock_adapter.return_value.configure.return_value = {
            "backups": [],
            "mcp_installed": True,
            "rules_injected": True,
            "skills_installed": False,
            "skills_supported": True,
        }
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "SKILL.md 규칙 파일 설치 실패" in captured.out

    def test_setup_skills_unsupported(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        mock_adapter.return_value.configure.return_value = {
            "backups": [],
            "mcp_installed": True,
            "rules_injected": True,
            "skills_supported": False,
        }
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "SKILL.md 규칙 파일 미지원" in captured.out

    def test_setup_semantic_search_installed(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        # sentence-transformers already installed → hits line 134
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        monkeypatch.setattr(
            "importlib.util.find_spec",
            lambda name: True if name == "sentence_transformers" else None,
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "semantic search" in captured.out
        assert "설치됨" in captured.out

    def test_setup_semantic_search_tty_yes(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        # TTY prompt, user says yes, install succeeds → lines 138-157
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        monkeypatch.setattr(
            "importlib.util.find_spec",
            lambda _name: None,
        )
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _prompt: "y")
        monkeypatch.setattr(
            "subprocess.run",
            lambda _cmd, check: None,
        )
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "sentence-transformers 설치 완료" in captured.out

    def test_setup_semantic_search_tty_no(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        # TTY prompt, user says no → lines 161-163
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        monkeypatch.setattr(
            "importlib.util.find_spec",
            lambda _name: None,
        )
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "설치를 생략합니다" in captured.out

    def test_setup_semantic_search_tty_eof(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        # TTY prompt, EOFError → line 142-143, then falls through to no branch
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        monkeypatch.setattr(
            "importlib.util.find_spec",
            lambda _name: None,
        )
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError()))
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "설치를 생략합니다" in captured.out

    def test_setup_semantic_search_tty_install_fail(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        # TTY prompt, user says yes, install fails → lines 158-160
        import subprocess

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        monkeypatch.setattr(
            "importlib.util.find_spec",
            lambda _name: None,
        )
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _prompt: "y")

        def _raise(*_args, **_kwargs):
            raise subprocess.CalledProcessError(1, "pip")

        monkeypatch.setattr("subprocess.run", _raise)
        args = MagicMock()
        args.agents = None
        args.scope = "user"
        assert cmd_setup(args) == 0
        captured = capsys.readouterr()
        assert "설치 실패" in captured.out


class TestCmdRestore:
    def test_restore_success(self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        assert cmd_restore(args) == 0
        captured = capsys.readouterr()
        assert "복원 완료" in captured.out
        mock_adapter.return_value.restore.assert_called_once()

    def test_restore_detected_but_no_backup(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        # Adapter detected but restore returns False → hits line 184
        mock_adapter.return_value.restore.return_value = False
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.ADAPTER_REGISTRY",
            {"mock": mock_adapter},
        )
        args = MagicMock()
        assert cmd_restore(args) == 0
        captured = capsys.readouterr()
        assert "복원할 백업 없음" in captured.out

    def test_restore_no_backups(
        self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock
    ) -> None:
        # Ensure no adapter is detected → hits line 189
        mock_adapter.return_value.detect.return_value = False
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.ADAPTER_REGISTRY",
            {"mock": mock_adapter},
        )
        args = MagicMock()
        assert cmd_restore(args) == 0
        captured = capsys.readouterr()
        assert "복원할 백업을 찾을 수 없습니다" in captured.out


class TestCmdCheck:
    def test_check_all_ok(self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        assert cmd_check(args) == 0
        captured = capsys.readouterr()
        assert "MockAgent" in captured.out

    def test_check_some_fail(self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock) -> None:
        mock_adapter.return_value.install_mcp.return_value = False
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        args = MagicMock()
        assert cmd_check(args) == 1
        captured = capsys.readouterr()
        assert "MockAgent" in captured.out


class TestMain:
    def test_list_subcommand(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"claude": True},
        )
        assert main(["setup", "--list"]) == 0
        captured = capsys.readouterr()
        assert "Claude" in captured.out

    def test_restore_subcommand(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        assert main(["setup", "--restore"]) == 0

    def test_check_subcommand(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        assert main(["setup", "--check"]) == 0

    def test_default_setup(self, monkeypatch: Any, capsys: Any, mock_adapter: MagicMock) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.detect_agents",
            lambda: {"mock": True},
        )
        assert main(["setup"]) == 0

    def test_python_incompatible(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.ensure_compatible_python",
            lambda: 1,
        )
        assert main([]) == 1

    def test_default_no_subcommand(self, monkeypatch: Any) -> None:
        # main([]) with no subcommand → hits line 280 (default cmd_setup)
        calls: list = []

        def _fake_cmd_setup(args):
            calls.append(True)
            return 0

        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.cmd_setup",
            _fake_cmd_setup,
        )
        assert main([]) == 0
        assert calls
