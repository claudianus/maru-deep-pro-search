"""Tests for self-update utilities."""

from __future__ import annotations

from maru_deep_pro_search.utils.updater import (
    UpdateCheckResult,
    _parse_version,
    _version_is_newer,
    get_update_notice,
    should_check_update,
)


class TestVersionParsing:
    def test_simple_versions(self):
        assert _parse_version("1.2.3") == (1, 2, 3)
        assert _parse_version("0.10.0") == (0, 10, 0)

    def test_strips_prerelease(self):
        assert _parse_version("1.2.3-beta") == (1, 2, 3)
        assert _parse_version("1.2.3+build") == (1, 2, 3)

    def test_short_versions(self):
        assert _parse_version("1.0") == (
            1,
            0,
        )


class TestVersionComparison:
    def test_newer(self):
        assert _version_is_newer("0.9.3", "0.10.0") is True
        assert _version_is_newer("1.0.0", "1.0.1") is True
        assert _version_is_newer("1.0.0", "2.0.0") is True

    def test_same(self):
        assert _version_is_newer("0.10.0", "0.10.0") is False

    def test_older(self):
        assert _version_is_newer("0.10.0", "0.9.3") is False


class TestUpdateNotice:
    def test_notice_when_update_available(self):
        result = UpdateCheckResult(
            current_version="0.9.3",
            latest_version="0.10.0",
            update_available=True,
        )
        notice = get_update_notice(result)
        assert notice is not None
        assert "0.9.3" in notice
        assert "0.10.0" in notice
        assert "maru-deep-pro-search update" in notice

    def test_no_notice_when_up_to_date(self):
        result = UpdateCheckResult(
            current_version="0.10.0",
            latest_version="0.10.0",
            update_available=False,
        )
        assert get_update_notice(result) is None

    def test_no_notice_on_error(self):
        result = UpdateCheckResult(
            current_version="0.10.0",
            latest_version=None,
            update_available=False,
            error="network error",
        )
        assert get_update_notice(result) is None


class TestShouldCheckUpdate:
    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("MARU_SKIP_UPDATE_CHECK", "1")
        assert should_check_update() is False

    def test_no_cooldown_always_checks(self, monkeypatch):
        monkeypatch.delenv("MARU_SKIP_UPDATE_CHECK", raising=False)
        assert should_check_update() is True


class TestGetInstalledVersion:
    def test_from_importlib_metadata(self, monkeypatch):
        import importlib.metadata
        monkeypatch.setattr(
            importlib.metadata,
            "version",
            lambda name: "1.2.3",
        )
        from maru_deep_pro_search.utils.updater import _get_installed_version
        assert _get_installed_version() == "1.2.3"

    def test_fallback_to_pyproject(self):
        from maru_deep_pro_search.utils.updater import _get_installed_version
        # importlib.metadata may fail since package isn't installed as wheel
        # It should fall back to pyproject.toml
        result = _get_installed_version()
        assert result != "0.0.0"

    def test_fallback_to_zero(self, monkeypatch):
        import importlib.metadata
        monkeypatch.setattr(
            importlib.metadata,
            "version",
            lambda name: (_ for _ in ()).throw(ImportError()),
        )
        import tomllib
        monkeypatch.setattr(
            tomllib,
            "load",
            lambda f: (_ for _ in ()).throw(IOError("no pyproject")),
        )
        from maru_deep_pro_search.utils.updater import _get_installed_version
        result = _get_installed_version()
        assert result == "0.0.0"


class TestGetLatestVersion:
    def test_success(self, monkeypatch):
        from io import BytesIO
        from unittest.mock import MagicMock
        from maru_deep_pro_search.utils.updater import _get_latest_version

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"info": {"version": "1.2.3"}}'
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_cm.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.urlopen",
            lambda req, timeout: mock_cm,
        )
        assert _get_latest_version() == "1.2.3"

    def test_failure(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import _get_latest_version
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.urlopen",
            lambda req, timeout: (_ for _ in ()).throw(IOError("network down")),
        )
        assert _get_latest_version() is None


class TestCheckForUpdate:
    def test_update_available(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import check_for_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "0.9.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        result = check_for_update()
        assert result.update_available is True
        assert result.latest_version == "1.0.0"

    def test_no_update(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import check_for_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "1.0.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        result = check_for_update()
        assert result.update_available is False

    def test_pypi_unreachable(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import check_for_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "1.0.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: None,
        )
        result = check_for_update()
        assert result.update_available is False
        assert result.error is not None


class TestPerformUpdate:
    def test_already_up_to_date(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import perform_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "1.0.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        success, msg = perform_update()
        assert success is True
        assert "up to date" in msg

    def test_dry_run(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import perform_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "0.9.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        success, msg = perform_update(dry_run=True)
        assert success is True
        assert "Would update" in msg

    def test_pypi_unreachable(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import perform_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: None,
        )
        success, msg = perform_update()
        assert success is False
        assert "network" in msg.lower() or "Could not" in msg

    def test_uv_update_success(self, monkeypatch):
        from unittest.mock import MagicMock
        from maru_deep_pro_search.utils.updater import perform_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "0.9.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.shutil.which",
            lambda cmd: "/usr/bin/uv" if cmd == "uv" else None,
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.subprocess.run",
            lambda *a, **kw: mock_result,
        )
        success, msg = perform_update()
        assert success is True
        assert "Updated" in msg

    def test_all_commands_fail(self, monkeypatch):
        from unittest.mock import MagicMock
        from maru_deep_pro_search.utils.updater import perform_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "0.9.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.shutil.which",
            lambda cmd: None,
        )
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.subprocess.run",
            lambda *a, **kw: mock_result,
        )
        success, msg = perform_update()
        assert success is False
        assert "failed" in msg.lower() or "Try manually" in msg

    def test_pipx_path(self, monkeypatch):
        from unittest.mock import MagicMock
        from maru_deep_pro_search.utils.updater import perform_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "0.9.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        # uv not available, pipx available
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.shutil.which",
            lambda cmd: "/usr/bin/pipx" if cmd == "pipx" else None,
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.subprocess.run",
            lambda *a, **kw: mock_result,
        )
        success, msg = perform_update()
        assert success is True

    def test_subprocess_exception(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import perform_update
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "0.9.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.shutil.which",
            lambda cmd: "/usr/bin/uv",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater.subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("fork failed")),
        )
        success, msg = perform_update()
        assert success is False

    def test_tomllib_fallback(self, monkeypatch, tmp_path):
        import importlib.metadata
        monkeypatch.setattr(
            importlib.metadata,
            "version",
            lambda name: (_ for _ in ()).throw(ImportError()),
        )
        # tomllib should find pyproject.toml
        from maru_deep_pro_search.utils.updater import _get_installed_version
        result = _get_installed_version()
        assert result != "0.0.0"


class TestMaybeNotifyUpdate:
    def test_skipped_when_env_set(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import maybe_notify_update
        monkeypatch.setenv("MARU_SKIP_UPDATE_CHECK", "1")
        assert maybe_notify_update() is None

    def test_returns_notice_when_update_available(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import maybe_notify_update
        monkeypatch.delenv("MARU_SKIP_UPDATE_CHECK", raising=False)
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "0.9.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        notice = maybe_notify_update()
        assert notice is not None
        assert "Update available" in notice

    def test_returns_none_when_up_to_date(self, monkeypatch):
        from maru_deep_pro_search.utils.updater import maybe_notify_update
        monkeypatch.delenv("MARU_SKIP_UPDATE_CHECK", raising=False)
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_installed_version",
            lambda: "1.0.0",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.utils.updater._get_latest_version",
            lambda: "1.0.0",
        )
        assert maybe_notify_update() is None
