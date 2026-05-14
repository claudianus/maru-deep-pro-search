"""Tests for agent auto-detection logic."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from maru_deep_pro_search.cli.detect import (
    AGENT_DETECTORS,
    detect_agents,
    installed_agents,
)


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: Any) -> Path:
    """Return a temporary directory acting as the user's home."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def which_map(monkeypatch: Any) -> dict[str, str]:
    """Mock shutil.which with a configurable command -> path map."""
    mapping: dict[str, str] = {}
    original = shutil.which

    def _which(cmd: str, mode: int = 1, path: str | None = None) -> str | None:
        return mapping.get(cmd)

    monkeypatch.setattr(shutil, "which", _which)
    return mapping


class TestDetectAgentsDefault:
    def test_all_false_by_default(self, fake_home: Path) -> None:
        result = detect_agents()
        assert all(v is False for v in result.values())
        assert set(result.keys()) == set(AGENT_DETECTORS.keys())

    def test_installed_agents_empty_by_default(self, fake_home: Path) -> None:
        assert installed_agents() == []


class TestDetectorsPositive:
    """Each detector returns True when its primary signal is present."""

    def test_claude_via_home_dir(self, fake_home: Path) -> None:
        fake_home.joinpath(".claude").mkdir()
        assert AGENT_DETECTORS["claude"]()

    def test_claude_via_json(self, fake_home: Path) -> None:
        fake_home.joinpath(".claude.json").touch()
        assert AGENT_DETECTORS["claude"]()

    def test_claude_via_which(self, which_map: dict[str, str]) -> None:
        which_map["claude"] = "/usr/bin/claude"
        assert AGENT_DETECTORS["claude"]()

    def test_cursor_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".cursor").mkdir()
        assert AGENT_DETECTORS["cursor"]()

    def test_cursor_via_project(self, tmp_path: Path, monkeypatch: Any) -> None:
        monkeypatch.chdir(tmp_path)
        tmp_path.joinpath(".cursor").mkdir()
        assert AGENT_DETECTORS["cursor"]()

    def test_cursor_via_which(self, which_map: dict[str, str]) -> None:
        which_map["cursor"] = "/usr/bin/cursor"
        assert AGENT_DETECTORS["cursor"]()

    def test_kimi_via_which(self, which_map: dict[str, str]) -> None:
        which_map["kimi"] = "/usr/bin/kimi"
        assert AGENT_DETECTORS["kimi"]()

    def test_kimi_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".kimi").mkdir()
        assert AGENT_DETECTORS["kimi"]()

    def test_antigravity(self, fake_home: Path) -> None:
        fake_home.joinpath(".gemini", "antigravity").mkdir(parents=True)
        assert AGENT_DETECTORS["antigravity"]()

    def test_kilo_via_config(self, fake_home: Path) -> None:
        fake_home.joinpath(".config", "kilo").mkdir(parents=True)
        assert AGENT_DETECTORS["kilo"]()

    def test_kilo_via_which(self, which_map: dict[str, str]) -> None:
        which_map["kilo"] = "/usr/bin/kilo"
        assert AGENT_DETECTORS["kilo"]()

    def test_opencode_via_which(self, which_map: dict[str, str]) -> None:
        which_map["opencode"] = "/usr/bin/opencode"
        assert AGENT_DETECTORS["opencode"]()

    def test_opencode_via_config(self, fake_home: Path) -> None:
        fake_home.joinpath(".config", "opencode").mkdir(parents=True)
        assert AGENT_DETECTORS["opencode"]()

    def test_windsurf_via_project(self, tmp_path: Path, monkeypatch: Any) -> None:
        monkeypatch.chdir(tmp_path)
        tmp_path.joinpath(".windsurf").mkdir()
        assert AGENT_DETECTORS["windsurf"]()

    def test_windsurf_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".windsurf").mkdir()
        assert AGENT_DETECTORS["windsurf"]()

    def test_windsurf_via_which(self, which_map: dict[str, str]) -> None:
        which_map["windsurf"] = "/usr/bin/windsurf"
        assert AGENT_DETECTORS["windsurf"]()

    def test_aider(self, which_map: dict[str, str]) -> None:
        which_map["aider"] = "/usr/bin/aider"
        assert AGENT_DETECTORS["aider"]()

    def test_copilot_via_code(self, which_map: dict[str, str]) -> None:
        which_map["code"] = "/usr/bin/code"
        assert AGENT_DETECTORS["copilot"]()

    def test_copilot_via_gh(self, which_map: dict[str, str]) -> None:
        which_map["gh"] = "/usr/bin/gh"
        assert AGENT_DETECTORS["copilot"]()

    def test_copilot_via_vscode(self, fake_home: Path) -> None:
        fake_home.joinpath(".vscode", "extensions").mkdir(parents=True)
        assert AGENT_DETECTORS["copilot"]()

    def test_continue_via_yaml(self, fake_home: Path) -> None:
        fake_home.joinpath(".continue", "config.yaml").parent.mkdir(parents=True)
        fake_home.joinpath(".continue", "config.yaml").touch()
        assert AGENT_DETECTORS["continue"]()

    def test_continue_via_json(self, fake_home: Path) -> None:
        fake_home.joinpath(".continue", "config.json").parent.mkdir(parents=True)
        fake_home.joinpath(".continue", "config.json").touch()
        assert AGENT_DETECTORS["continue"]()

    def test_continue_via_xdg(self, fake_home: Path) -> None:
        fake_home.joinpath(".config", "continue", "config.json").parent.mkdir(parents=True)
        fake_home.joinpath(".config", "continue", "config.json").touch()
        assert AGENT_DETECTORS["continue"]()

    def test_cline_via_saoudrizwan(self, fake_home: Path) -> None:
        fake_home.joinpath(".vscode", "extensions", "saoudrizwan.claude-dev").mkdir(parents=True)
        assert AGENT_DETECTORS["cline"]()

    def test_cline_via_claude_dev(self, fake_home: Path) -> None:
        fake_home.joinpath(".vscode", "extensions", "claude-dev").mkdir(parents=True)
        assert AGENT_DETECTORS["cline"]()

    def test_zed_via_which(self, which_map: dict[str, str]) -> None:
        which_map["zed"] = "/usr/bin/zed"
        assert AGENT_DETECTORS["zed"]()

    def test_zed_via_config(self, fake_home: Path) -> None:
        fake_home.joinpath(".config", "zed").mkdir(parents=True)
        assert AGENT_DETECTORS["zed"]()

    def test_zed_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".zed").mkdir()
        assert AGENT_DETECTORS["zed"]()

    def test_jetbrains_via_which_idea(self, which_map: dict[str, str]) -> None:
        which_map["idea"] = "/usr/bin/idea"
        assert AGENT_DETECTORS["jetbrains"]()

    def test_jetbrains_via_which_webstorm(self, which_map: dict[str, str]) -> None:
        which_map["webstorm"] = "/usr/bin/webstorm"
        assert AGENT_DETECTORS["jetbrains"]()

    def test_jetbrains_via_which_pycharm(self, which_map: dict[str, str]) -> None:
        which_map["pycharm"] = "/usr/bin/pycharm"
        assert AGENT_DETECTORS["jetbrains"]()

    def test_jetbrains_via_home_dir(self, fake_home: Path) -> None:
        fake_home.joinpath(".jetbrains").mkdir()
        assert AGENT_DETECTORS["jetbrains"]()

    def test_supermaven_via_which(self, which_map: dict[str, str]) -> None:
        which_map["supermaven"] = "/usr/bin/supermaven"
        assert AGENT_DETECTORS["supermaven"]()

    def test_supermaven_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".supermaven").mkdir()
        assert AGENT_DETECTORS["supermaven"]()

    def test_cody_via_which(self, which_map: dict[str, str]) -> None:
        which_map["cody"] = "/usr/bin/cody"
        assert AGENT_DETECTORS["cody"]()

    def test_cody_via_config(self, fake_home: Path) -> None:
        fake_home.joinpath(".config", "cody").mkdir(parents=True)
        assert AGENT_DETECTORS["cody"]()

    def test_cody_via_vscode_ext(self, fake_home: Path) -> None:
        ext = fake_home.joinpath(".vscode", "extensions", "sourcegraph.cody")
        ext.mkdir(parents=True)
        assert AGENT_DETECTORS["cody"]()

    def test_codeium_via_which(self, which_map: dict[str, str]) -> None:
        which_map["codeium"] = "/usr/bin/codeium"
        assert AGENT_DETECTORS["codeium"]()

    def test_codeium_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".codeium").mkdir()
        assert AGENT_DETECTORS["codeium"]()

    def test_codeium_via_vscode_ext(self, fake_home: Path) -> None:
        ext = fake_home.joinpath(".vscode", "extensions", "codeium.codeium")
        ext.mkdir(parents=True)
        assert AGENT_DETECTORS["codeium"]()

    def test_amazon_q_via_which(self, which_map: dict[str, str]) -> None:
        which_map["q"] = "/usr/bin/q"
        assert AGENT_DETECTORS["amazon_q"]()

    def test_amazon_q_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".aws", "amazonq").mkdir(parents=True)
        assert AGENT_DETECTORS["amazon_q"]()

    def test_amazon_q_via_vscode_ext(self, fake_home: Path) -> None:
        ext = fake_home.joinpath(".vscode", "extensions", "amazon-q-vscode")
        ext.mkdir(parents=True)
        assert AGENT_DETECTORS["amazon_q"]()

    def test_devin_via_which(self, which_map: dict[str, str]) -> None:
        which_map["devin"] = "/usr/bin/devin"
        assert AGENT_DETECTORS["devin"]()

    def test_devin_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".devin").mkdir()
        assert AGENT_DETECTORS["devin"]()

    def test_devin_via_project(self, tmp_path: Path, monkeypatch: Any) -> None:
        monkeypatch.chdir(tmp_path)
        tmp_path.joinpath(".devin").mkdir()
        assert AGENT_DETECTORS["devin"]()

    def test_tabnine_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".tabnine").mkdir()
        assert AGENT_DETECTORS["tabnine"]()

    def test_tabnine_via_vscode_ext(self, fake_home: Path) -> None:
        ext = fake_home.joinpath(".vscode", "extensions", "tabnine.tabnine")
        ext.mkdir(parents=True)
        assert AGENT_DETECTORS["tabnine"]()

    def test_hermes_via_which(self, which_map: dict[str, str]) -> None:
        which_map["hermes"] = "/usr/bin/hermes"
        assert AGENT_DETECTORS["hermes"]()

    def test_hermes_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".hermes").mkdir()
        assert AGENT_DETECTORS["hermes"]()

    def test_codex_via_which(self, which_map: dict[str, str]) -> None:
        which_map["codex"] = "/usr/bin/codex"
        assert AGENT_DETECTORS["codex"]()

    def test_codex_via_home(self, fake_home: Path) -> None:
        fake_home.joinpath(".codex").mkdir()
        assert AGENT_DETECTORS["codex"]()


class TestDetectorsNegative:
    """Each detector returns False when nothing is present."""

    def test_claude_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["claude"]() is False

    def test_cursor_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["cursor"]() is False

    def test_kimi_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["kimi"]() is False

    def test_antigravity_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["antigravity"]() is False

    def test_kilo_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["kilo"]() is False

    def test_opencode_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["opencode"]() is False

    def test_windsurf_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["windsurf"]() is False

    def test_aider_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["aider"]() is False

    def test_copilot_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["copilot"]() is False

    def test_continue_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["continue"]() is False

    def test_cline_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["cline"]() is False

    def test_zed_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["zed"]() is False

    def test_jetbrains_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["jetbrains"]() is False

    def test_supermaven_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["supermaven"]() is False

    def test_cody_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["cody"]() is False

    def test_codeium_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["codeium"]() is False

    def test_amazon_q_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["amazon_q"]() is False

    def test_devin_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["devin"]() is False

    def test_tabnine_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["tabnine"]() is False

    def test_hermes_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["hermes"]() is False

    def test_codex_negative(self, fake_home: Path) -> None:
        assert AGENT_DETECTORS["codex"]() is False


class TestInstalledAgents:
    def test_returns_detected_names(self, fake_home: Path) -> None:
        fake_home.joinpath(".claude").mkdir()
        fake_home.joinpath(".cursor").mkdir()
        result = installed_agents()
        assert "claude" in result
        assert "cursor" in result
