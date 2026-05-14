"""Tests for agent adapter base class."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from maru_deep_pro_search.cli.agents.base import (
    AgentAdapter,
    get_mcp_server_command,
    get_mcp_server_command_list,
    get_mcp_server_yaml,
)


class TestGetMcpServerCommand:
    def test_binary_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/maru-deep-pro-search")
        cmd = get_mcp_server_command()
        assert cmd["command"] == "/usr/bin/maru-deep-pro-search"
        assert cmd["args"] == []

    def test_binary_not_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        import sys
        cmd = get_mcp_server_command()
        assert cmd["command"] == sys.executable
        assert "-m" in cmd["args"]


class TestGetMcpServerCommandList:
    def test_binary_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/maru-deep-pro-search")
        cmd = get_mcp_server_command_list()
        assert cmd == ["/usr/bin/maru-deep-pro-search"]

    def test_binary_not_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        import sys
        cmd = get_mcp_server_command_list()
        assert cmd[0] == sys.executable
        assert "-m" in cmd


class TestGetMcpServerYaml:
    def test_binary_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/maru-deep-pro-search")
        yaml = get_mcp_server_yaml()
        assert "maru-deep-pro-search" in yaml
        assert "/usr/bin/maru-deep-pro-search" in yaml

    def test_binary_not_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        import sys
        yaml = get_mcp_server_yaml()
        assert "maru-deep-pro-search" in yaml
        assert sys.executable in yaml
        assert "-m" in yaml


class TestAgentAdapter:
    def test_skills_dir_returns_none(self):
        adapter = self._make_adapter()
        assert adapter._skills_dir("user") is None

    def test_install_skills_no_dir(self):
        adapter = self._make_adapter()
        assert adapter.install_skills("user") is False

    def test_install_skills_source_missing(self, monkeypatch):
        adapter = self._make_adapter()
        adapter._skills_dir = lambda scope: Path("/nonexistent")
        monkeypatch.setattr(
            adapter, "_get_skills_source_dir", lambda: Path("/nonexistent_source")
        )
        assert adapter.install_skills("user") is False

    def test_install_skills_flat_format(self, monkeypatch, tmp_path):
        adapter = self._make_adapter()
        source = tmp_path / "skills"
        skill_dir = source / "python"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Python")
        adapter._get_skills_source_dir = lambda: source
        target = tmp_path / "target"
        adapter._skills_dir = lambda scope: target
        assert adapter.install_skills("user") is True
        assert (target / "python.md").exists()

    def test_install_skills_nested_format(self, monkeypatch, tmp_path):
        adapter = self._make_adapter()
        adapter.skills_format = "nested"
        source = tmp_path / "skills"
        skill_dir = source / "rust"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Rust")
        adapter._get_skills_source_dir = lambda: source
        target = tmp_path / "target"
        adapter._skills_dir = lambda scope: target
        assert adapter.install_skills("user") is True
        assert (target / "rust" / "SKILL.md").exists()

    def test_install_skills_no_skills_file(self, tmp_path):
        adapter = self._make_adapter()
        source = tmp_path / "skills"
        (source / "empty_dir").mkdir(parents=True)
        adapter._get_skills_source_dir = lambda: source
        target = tmp_path / "target"
        adapter._skills_dir = lambda scope: target
        assert adapter.install_skills("user") is False

    def test_configure(self, tmp_path):
        adapter = self._make_adapter()
        adapter.backup = lambda: [tmp_path / "bak"]
        adapter.install_mcp = lambda scope: True
        adapter.inject_rules = lambda scope: True
        adapter._skills_dir = lambda scope: tmp_path / "skills"
        result = adapter.configure("user")
        assert result["mcp_installed"] is True
        assert result["rules_injected"] is True
        assert result["skills_supported"] is True
        assert result["success"] is True
        assert str(tmp_path / "bak") in result["backups"]

    def test_configure_no_skills_support(self):
        adapter = self._make_adapter()
        adapter.backup = lambda: []
        adapter.install_mcp = lambda scope: True
        adapter.inject_rules = lambda scope: True
        adapter._skills_dir = lambda scope: None
        result = adapter.configure("user")
        assert result["skills_supported"] is False
        assert result["skills_installed"] is None
        assert result["success"] is True

    def _make_adapter(self):
        """Create a concrete adapter for testing."""
        class TestAdapter(AgentAdapter):
            name = "test"
            display_name = "Test Agent"

            def detect(self):
                return True

            def install_mcp(self, scope="user"):
                return True

            def inject_rules(self, scope="user"):
                return True

            def backup(self):
                return []

            def restore(self):
                return True

        return TestAdapter()
