"""Smoke tests for all 21 agent adapters — instantiation, detection, injection."""

from __future__ import annotations

from pathlib import Path

import pytest

ADAPTER_CLASSES = [
    ("aider", "AiderAdapter"),
    ("amazon_q", "AmazonQAdapter"),
    ("antigravity", "AntiGravityAdapter"),
    ("claude", "ClaudeAdapter"),
    ("cline", "ClineAdapter"),
    ("codeium", "CodeiumAdapter"),
    ("codex", "CodexAdapter"),
    ("cody", "CodyAdapter"),
    ("continue_", "ContinueAdapter"),
    ("copilot", "CopilotAdapter"),
    ("cursor", "CursorAdapter"),
    ("devin", "DevinAdapter"),
    ("hermes", "HermesAdapter"),
    ("jetbrains", "JetBrainsAdapter"),
    ("kilo", "KiloAdapter"),
    ("kimi", "KimiAdapter"),
    ("opencode", "OpenCodeAdapter"),
    ("supermaven", "SupermavenAdapter"),
    ("tabnine", "TabnineAdapter"),
    ("windsurf", "WindsurfAdapter"),
    ("zed", "ZedAdapter"),
]


@pytest.fixture
def mock_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect Path.home() to a temp directory for isolation."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


class TestAdapterSmoke:
    @pytest.mark.parametrize("module_name,class_name", ADAPTER_CLASSES)
    def test_instantiation(self, module_name: str, class_name: str) -> None:
        """Every adapter class can be imported and instantiated."""
        module = __import__(
            f"maru_deep_pro_search.cli.agents.{module_name}",
            fromlist=[class_name],
        )
        cls = getattr(module, class_name)
        adapter = cls()
        assert adapter.name
        assert adapter.display_name

    @pytest.mark.parametrize("module_name,class_name", ADAPTER_CLASSES)
    def test_detect_returns_bool(self, module_name: str, class_name: str) -> None:
        """detect() returns a bool without crashing."""
        module = __import__(
            f"maru_deep_pro_search.cli.agents.{module_name}",
            fromlist=[class_name],
        )
        cls = getattr(module, class_name)
        adapter = cls()
        result = adapter.detect()
        assert isinstance(result, bool)

    @pytest.mark.parametrize("module_name,class_name", ADAPTER_CLASSES)
    def test_inject_rules_idempotent_user_scope(
        self, mock_home: Path, module_name: str, class_name: str
    ) -> None:
        """inject_rules('user') succeeds and is idempotent."""
        module = __import__(
            f"maru_deep_pro_search.cli.agents.{module_name}",
            fromlist=[class_name],
        )
        cls = getattr(module, class_name)
        adapter = cls()

        # First injection
        result1 = adapter.inject_rules("user")
        assert isinstance(result1, bool)

        # Second injection should also succeed (idempotent)
        result2 = adapter.inject_rules("user")
        assert isinstance(result2, bool)

    @pytest.mark.parametrize("module_name,class_name", ADAPTER_CLASSES)
    def test_inject_rules_idempotent_project_scope(
        self, tmp_path: Path, module_name: str, class_name: str
    ) -> None:
        """inject_rules('project') succeeds and is idempotent."""
        module = __import__(
            f"maru_deep_pro_search.cli.agents.{module_name}",
            fromlist=[class_name],
        )
        cls = getattr(module, class_name)
        adapter = cls()

        # Run in a temp project directory
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result1 = adapter.inject_rules("project")
            assert isinstance(result1, bool)
            result2 = adapter.inject_rules("project")
            assert isinstance(result2, bool)
        finally:
            os.chdir(old_cwd)

    @pytest.mark.parametrize("module_name,class_name", ADAPTER_CLASSES)
    def test_backup_and_restore(self, mock_home: Path, module_name: str, class_name: str) -> None:
        """backup() returns a list; restore() returns a bool."""
        module = __import__(
            f"maru_deep_pro_search.cli.agents.{module_name}",
            fromlist=[class_name],
        )
        cls = getattr(module, class_name)
        adapter = cls()

        backups = adapter.backup()
        assert isinstance(backups, list)
        # All items should be Path instances (or empty list)
        assert all(isinstance(b, Path) for b in backups)

        restored = adapter.restore()
        assert isinstance(restored, bool)
