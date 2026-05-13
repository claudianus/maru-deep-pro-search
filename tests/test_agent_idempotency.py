"""Tests for agent adapter idempotency on reinstall."""

from __future__ import annotations

from maru_deep_pro_search.cli.agents.codex import CodexAdapter


class TestCodexAdapter:
    def test_insert_features_idempotent(self):
        """Adding [features] twice must not duplicate the section."""
        lines = ["[mcp_servers.test]", 'command = "test"']
        lines = CodexAdapter._insert_or_update_features(lines)
        assert lines.count("[features]") == 1
        assert "codex_hooks = true" in lines

        # Second call must not duplicate
        lines = CodexAdapter._insert_or_update_features(lines)
        assert lines.count("[features]") == 1
        assert lines.count("codex_hooks = true") == 1

    def test_insert_features_into_existing_section(self):
        """If [features] already exists with other keys, insert inside it."""
        lines = [
            "[features]",
            "auto_commit = true",
            "",
            "[mcp_servers.test]",
        ]
        lines = CodexAdapter._insert_or_update_features(lines)
        assert lines.count("[features]") == 1
        assert "codex_hooks = true" in lines
        assert "auto_commit = true" in lines

        # Second call must not duplicate
        lines = CodexAdapter._insert_or_update_features(lines)
        assert lines.count("[features]") == 1
        assert lines.count("codex_hooks = true") == 1

    def test_remove_developer_instructions_multiline(self):
        """Old developer_instructions block must be fully removed."""
        lines = [
            'developer_instructions = """',
            "Always research first.",
            "Then code.",
            '"""',
            "",
            "[features]",
        ]
        result = CodexAdapter._remove_developer_instructions(lines)
        assert 'developer_instructions = """' not in result
        assert "Always research first." not in result
        assert "Then code." not in result
        assert '"""' not in result
        assert "[features]" in result

    def test_remove_developer_instructions_single_line(self):
        """Single-line developer_instructions must be removed."""
        lines = [
            'developer_instructions = "Always research first"',
            "",
            "[features]",
        ]
        result = CodexAdapter._remove_developer_instructions(lines)
        assert "developer_instructions" not in result
        assert "[features]" in result

    def test_remove_developer_instructions_single_line_ml(self):
        """Single-line multiline string must be removed."""
        lines = [
            'developer_instructions = """Always research first"""',
            "",
            "[features]",
        ]
        result = CodexAdapter._remove_developer_instructions(lines)
        assert "developer_instructions" not in result
        assert "Always research first" not in result
        assert "[features]" in result

    def test_remove_developer_instructions_idempotent(self):
        """Running removal twice on already-clean content must be safe."""
        lines = [
            "[features]",
            "codex_hooks = true",
        ]
        result = CodexAdapter._remove_developer_instructions(lines)
        assert result == lines

    def test_has_approval_policy(self):
        assert CodexAdapter._has_approval_policy(['approval_policy = "on-request"'])
        assert not CodexAdapter._has_approval_policy(["# approval_policy comment"])
        assert not CodexAdapter._has_approval_policy(["some_key = 'approval_policy value'"])


class TestHermesAdapter:
    def test_plugin_insert_into_empty_config(self):
        """First install: create plugins section."""
        lines = ["mcp_servers:", "  test:", "    command: test"]
        content = "\n".join(lines) + "\n"
        lines_out = content.splitlines()
        plugins_idx = None
        for i, line in enumerate(lines_out):
            if line.rstrip() == "plugins:":
                plugins_idx = i
            if "maru-research-gate" in line:
                break

        if plugins_idx is None:
            lines_out.append("plugins:")
            lines_out.append("  enabled:")
            lines_out.append("    - maru-research-gate")

        assert "plugins:" in lines_out
        assert "    - maru-research-gate" in lines_out

    def test_plugin_insert_with_existing_plugins(self):
        """Install when other plugins already exist."""
        lines = [
            "plugins:",
            "  enabled:",
            "    - other-plugin",
            "",
            "mcp_servers:",
        ]
        lines_out = list(lines)
        plugins_idx = None
        enabled_idx = None
        for i, line in enumerate(lines_out):
            if line.rstrip() == "plugins:":
                plugins_idx = i
            if plugins_idx is not None and line.strip() == "enabled:":
                enabled_idx = i
            if "maru-research-gate" in line:
                break

        if plugins_idx is not None and enabled_idx is not None:
            lines_out.insert(enabled_idx + 1, "    - maru-research-gate")

        assert lines_out.count("    - maru-research-gate") == 1
        assert "    - other-plugin" in lines_out

    def test_plugin_idempotent(self):
        """Reinstall must not duplicate maru-research-gate."""
        lines = [
            "plugins:",
            "  enabled:",
            "    - maru-research-gate",
            "    - other-plugin",
        ]
        lines_out = list(lines)
        plugins_idx = None
        enabled_idx = None
        skip_insert = False
        for i, line in enumerate(lines_out):
            if line.rstrip() == "plugins:":
                plugins_idx = i
            if plugins_idx is not None and line.strip() == "enabled:":
                enabled_idx = i
            if "maru-research-gate" in line:
                skip_insert = True

        if plugins_idx is not None and enabled_idx is not None and not skip_insert:
            lines_out.insert(enabled_idx + 1, "    - maru-research-gate")

        assert lines_out.count("    - maru-research-gate") == 1
