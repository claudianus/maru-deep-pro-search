"""Tests for environment validation helpers."""

from __future__ import annotations

import subprocess
import sys
from collections import namedtuple
from typing import Any
from unittest.mock import MagicMock

from maru_deep_pro_search.cli.env_check import (
    MIN_PY_MAJOR,
    MIN_PY_MINOR,
    bold,
    current_python_version,
    ensure_compatible_python,
    find_uv,
    green,
    has_pyenv,
    install_python_via_uv,
    install_uv,
    is_python_compatible,
    print_environment_report,
    red,
)


class TestColorHelpers:
    def test_bold_wraps_ansi(self) -> None:
        assert bold("hello") == "\033[1mhello\033[0m"

    def test_red_wraps_ansi(self) -> None:
        assert red("hello") == "\033[31mhello\033[0m"

    def test_green_wraps_ansi(self) -> None:
        assert green("hello") == "\033[32mhello\033[0m"


_VersionInfo = namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])


class TestPythonVersion:
    def test_current_python_version(self) -> None:
        major, minor, micro = current_python_version()
        assert major == sys.version_info.major
        assert minor == sys.version_info.minor
        assert micro == sys.version_info.micro

    def test_is_python_compatible_true(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        assert is_python_compatible() is True

    def test_is_python_compatible_exact(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            sys, "version_info", _VersionInfo(MIN_PY_MAJOR, MIN_PY_MINOR, 0, "final", 0)
        )
        assert is_python_compatible() is True

    def test_is_python_compatible_false(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 9, 0, "final", 0))
        assert is_python_compatible() is False

    def test_is_python_compatible_newer_major(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(4, 0, 0, "final", 0))
        assert is_python_compatible() is True


class TestFindUv:
    def test_find_uv_in_path(self, monkeypatch: Any) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/uv" if cmd == "uv" else None)
        assert find_uv() == "/usr/bin/uv"

    def test_find_uv_not_found(self, monkeypatch: Any) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        assert find_uv() is None


class TestHasPyenv:
    def test_has_pyenv_true(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/pyenv" if cmd == "pyenv" else None
        )
        assert has_pyenv() is True

    def test_has_pyenv_false(self, monkeypatch: Any) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        assert has_pyenv() is False


class TestInstallUv:
    def test_success(self, monkeypatch: Any) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: mock_result,
        )
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/uv" if cmd == "uv" else None)
        assert install_uv() == "/usr/bin/uv"

    def test_failure(self, monkeypatch: Any) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: mock_result,
        )
        assert install_uv() is None

    def test_exception(self, monkeypatch: Any) -> None:
        def _raise(*args, **kwargs):
            raise OSError("boom")

        monkeypatch.setattr("subprocess.run", _raise)
        assert install_uv() is None


class TestInstallPythonViaUv:
    def test_success(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: MagicMock(),
        )
        assert install_python_via_uv("/usr/bin/uv", "3.12") is True

    def test_failure(self, monkeypatch: Any) -> None:
        def _raise(*args, **kwargs):
            raise subprocess.CalledProcessError(1, ["uv"])

        monkeypatch.setattr("subprocess.run", _raise)
        assert install_python_via_uv("/usr/bin/uv", "3.12") is False


class TestPrintEnvironmentReport:
    def test_compatible(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/uv" if cmd == "uv" else None)
        print_environment_report()
        captured = capsys.readouterr()
        assert "Python 3.12.0" in captured.out
        assert "uv" in captured.out

    def test_incompatible(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 9, 0, "final", 0))
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        print_environment_report()
        captured = capsys.readouterr()
        assert "3.9.0" in captured.out
        assert "uv" in captured.out


class TestEnsureCompatiblePython:
    def test_already_compatible(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        assert ensure_compatible_python() == 0
        captured = capsys.readouterr()
        assert "3.12.0" in captured.out

    def test_incompatible_no_uv(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 9, 0, "final", 0))
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.env_check.install_uv",
            lambda: None,
        )
        assert ensure_compatible_python() == 1
        captured = capsys.readouterr()
        assert "지원되지 않습니다" in captured.out

    def test_incompatible_uv_installs_python(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 9, 0, "final", 0))
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/uv" if cmd == "uv" else None)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.env_check.install_python_via_uv",
            lambda uv, ver: True,
        )
        assert ensure_compatible_python() == 1
        captured = capsys.readouterr()
        assert "3.10" in captured.out

    def test_incompatible_uv_fails_python(self, monkeypatch: Any, capsys: Any) -> None:
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 9, 0, "final", 0))
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/uv" if cmd == "uv" else None)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.env_check.install_python_via_uv",
            lambda uv, ver: False,
        )
        assert ensure_compatible_python() == 1
        captured = capsys.readouterr()
        assert "설치 실패" in captured.out
