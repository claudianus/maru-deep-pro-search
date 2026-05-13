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
