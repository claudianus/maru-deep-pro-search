"""Tests for agent harness specification."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from maru_deep_pro_search.harness.spec import (
    HarnessSpec,
    LifecycleHook,
    QualityGate,
)


class TestHarnessSpec:
    @pytest.fixture(autouse=True)
    def _mock_yaml(self, monkeypatch):
        yaml_mod = MagicMock()
        yaml_mod.safe_load = lambda s: {
            "mcp_servers": {"test-server": {"command": "python"}},
            "research_protocol": "test protocol",
            "commands": [
                {"name": "testcmd", "description": "A test command", "prompt": "Do a test"}
            ],
            "rules": [{"scope": "global", "content": "Always test"}],
            "hooks": [
                {"event": "post_tool_use", "matcher": "*", "action": "prompt", "prompt": "verify"}
            ],
            "quality_gates": [{"language": "python", "lint_cmd": "ruff check ."}],
            "conventions": ["TEST.md"],
            "knowledge_db_path": "custom.db",
            "plugins": ["my-plugin"],
        }
        monkeypatch.setitem(sys.modules, "yaml", yaml_mod)

    def test_default_creates_spec(self):
        spec = HarnessSpec.default()
        assert "maru-deep-pro-search" in spec.mcp_servers
        assert len(spec.commands) >= 1
        assert any(c.name == "research" for c in spec.commands)
        assert spec.research_protocol
        assert spec.knowledge_db_path == ".maru/knowledge.db"

    def test_from_project_with_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maru_dir = root / ".maru"
            maru_dir.mkdir()
            yaml_content = """
mcp_servers:
  test-server:
    command: python
research_protocol: "test protocol"
commands:
  - name: testcmd
    description: A test command
    prompt: Do a test
rules:
  - scope: global
    content: Always test
hooks:
  - event: post_tool_use
    matcher: "*"
    action: prompt
    prompt: "verify"
quality_gates:
  - language: python
    lint_cmd: ruff check .
conventions:
  - TEST.md
knowledge_db_path: custom.db
plugins:
  - my-plugin
"""
            (maru_dir / "harness.yaml").write_text(yaml_content, encoding="utf-8")
            spec = HarnessSpec.from_project(str(root))
            assert "test-server" in spec.mcp_servers
            assert spec.research_protocol == "test protocol"
            assert len(spec.commands) == 1
            assert spec.conventions == ["TEST.md"]
            assert spec.knowledge_db_path == "custom.db"
            assert spec.plugins == ["my-plugin"]

    def test_from_project_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = HarnessSpec.from_project(str(tmp))
            assert "maru-deep-pro-search" in spec.mcp_servers

    def test_to_agent_config_claude(self):
        spec = HarnessSpec.default()
        cfg = spec.to_agent_config("claude")
        assert "mcpServers" in cfg
        assert "settings" in cfg
        assert "commands" in cfg
        assert "rules" in cfg
        assert "claude_md" in cfg
        import sys

        assert cfg["mcpServers"]["maru-deep-pro-search"]["command"] == sys.executable

    def test_to_agent_config_aider(self):
        spec = HarnessSpec.default()
        cfg = spec.to_agent_config("aider")
        assert "read" in cfg
        assert "auto_lint" in cfg
        assert "lint_cmd" in cfg
        assert "conventions_md" in cfg

    def test_to_agent_config_cursor(self):
        spec = HarnessSpec.default()
        cfg = spec.to_agent_config("cursor")
        assert "mcpServers" in cfg
        assert "rules" in cfg
        assert "commands" in cfg

    def test_to_agent_config_copilot(self):
        spec = HarnessSpec.default()
        cfg = spec.to_agent_config("copilot")
        assert "instructions" in cfg
        assert "mcpServers" in cfg

    def test_to_agent_config_unknown(self):
        spec = HarnessSpec.default()
        assert spec.to_agent_config("unknown") == {}

    def test_to_claude_with_hooks(self):
        spec = HarnessSpec(
            mcp_servers={},
            commands=[],
            rules=[],
            hooks=[
                LifecycleHook(
                    event="post_tool_use",
                    matcher="Write|Edit",
                    action="command",
                    command="echo done",
                ),
            ],
        )
        cfg = spec._to_claude()
        assert len(cfg["settings"]["hooks"]["PostToolUse"]) == 1
        assert cfg["settings"]["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit"

    def test_to_aider_with_test_cmd(self):
        spec = HarnessSpec(
            quality_gates=[
                QualityGate(language="python", lint_cmd="ruff check .", test_cmd="pytest"),
            ],
        )
        cfg = spec._to_aider()
        assert cfg["auto_lint"] is True
        assert cfg["auto_test"] is True
        assert len(cfg["test_cmd"]) == 1

    def test_to_aider_no_quality_gates(self):
        spec = HarnessSpec(quality_gates=[])
        cfg = spec._to_aider()
        assert cfg["auto_lint"] is False
        assert cfg["auto_test"] is False

    def test_dataclass_defaults(self):
        spec = HarnessSpec()
        assert spec.mcp_servers == {}
        assert spec.commands == []
        assert spec.rules == []
        assert spec.hooks == []
        assert spec.quality_gates == []
        assert spec.conventions == []
        assert spec.plugins == []
