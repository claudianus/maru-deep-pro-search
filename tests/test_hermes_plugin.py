"""Tests for the Hermes research-gate plugin."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from maru_deep_pro_search.cli.agents.hermes_plugin import (
    _check_research,
    register,
)


@pytest.fixture(autouse=True)
def _isolate_session_file(monkeypatch: Any, tmp_path: Path) -> Path:
    """Redirect SESSION_FILE to a temp path for every test."""
    session = tmp_path / "session_research.json"
    monkeypatch.setattr(
        "maru_deep_pro_search.cli.agents.hermes_plugin.SESSION_FILE",
        session,
    )
    return session


class TestCheckResearch:
    def test_no_session_file(self) -> None:
        ok, msg = _check_research()
        assert ok is False
        assert "No research session" in msg

    def test_corrupted_file(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text("not json")
        ok, msg = _check_research()
        assert ok is False
        assert "Corrupted" in msg

    def test_missing_completed_at(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(json.dumps({"research_id": "RSCH-1"}))
        ok, msg = _check_research()
        assert ok is False
        assert "not marked" in msg

    def test_invalid_timestamp(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(json.dumps({"completed_at": "not-a-date", "research_id": "RSCH-1"}))
        ok, msg = _check_research()
        assert ok is False
        assert "Invalid timestamp" in msg

    def test_expired(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": (
                        datetime.now(timezone.utc) - timedelta(minutes=40)
                    ).isoformat(),
                    "research_id": "RSCH-1",
                }
            )
        )
        ok, msg = _check_research()
        assert ok is False
        assert "expired" in msg

    def test_invalid_research_id(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "research_id": "BAD-ID",
                }
            )
        )
        ok, msg = _check_research()
        assert ok is False
        assert "Invalid research_id" in msg

    def test_valid(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "research_id": "RSCH-12345",
                }
            )
        )
        ok, msg = _check_research()
        assert ok is True
        assert "RSCH-12345" in msg

    def test_valid_without_tz(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": datetime.now().replace(tzinfo=None).isoformat(),
                    "research_id": "RSCH-12345",
                }
            )
        )
        ok, msg = _check_research()
        assert ok is True


class TestRegister:
    def test_registers_all_hooks_and_commands(self) -> None:
        ctx = MagicMock()
        register(ctx)
        assert ctx.register_hook.call_count == 3
        assert ctx.register_command.call_count == 2
        assert ctx.register_cli_command.call_count == 1

    def test_pre_tool_call_exempts_deep_research(self) -> None:
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_hook.call_args_list
        pre_call = [c for c in calls if c[0][0] == "pre_tool_call"][0]
        handler = pre_call[0][1]
        assert handler("deep_research", {}) is None

    def test_pre_tool_call_blocks_without_research(self, tmp_path: Path) -> None:
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_hook.call_args_list
        pre_call = [c for c in calls if c[0][0] == "pre_tool_call"][0]
        handler = pre_call[0][1]
        result = handler("write_file", {})
        assert result is not None
        assert result["action"] == "block"

    def test_pre_tool_call_allows_with_research(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "research_id": "RSCH-12345",
                }
            )
        )
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_hook.call_args_list
        pre_call = [c for c in calls if c[0][0] == "pre_tool_call"][0]
        handler = pre_call[0][1]
        assert handler("web_search", {}) is None

    def test_pre_tool_call_warns_gated_tools(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "research_id": "RSCH-12345",
                }
            )
        )
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_hook.call_args_list
        pre_call = [c for c in calls if c[0][0] == "pre_tool_call"][0]
        handler = pre_call[0][1]
        assert handler("write_file", {}) is None
        ctx.inject_message.assert_called_once()

    def test_post_tool_call_logs(self, monkeypatch: Any) -> None:
        logged = {}
        mock_logger = MagicMock()
        mock_logger.log_tool_call = lambda **kw: logged.update(kw)
        monkeypatch.setattr(
            "maru_deep_pro_search.harness.audit.AuditLogger",
            lambda: mock_logger,
        )
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_hook.call_args_list
        post_call = [c for c in calls if c[0][0] == "post_tool_call"][0]
        handler = post_call[0][1]
        handler("fetch_page", {"url": "x"}, "result text")
        assert logged["tool_name"] == "fetch_page"

    def test_session_start_clears_file(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text("{}")
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_hook.call_args_list
        start_call = [c for c in calls if c[0][0] == "on_session_start"][0]
        handler = start_call[0][1]
        handler("sid-1")
        assert not session.exists()
        ctx.inject_message.assert_called_once()

    def test_cmd_research_empty_query(self) -> None:
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_command.call_args_list
        research_call = [c for c in calls if c[1].get("name") == "research"][0]
        handler = research_call[1]["handler"]
        assert handler("") == "Usage: /research <query>"

    def test_cmd_research_triggers(self, tmp_path: Path) -> None:
        ctx = MagicMock()
        ctx.dispatch_tool.return_value = "research done"
        register(ctx)
        calls = ctx.register_command.call_args_list
        research_call = [c for c in calls if c[1].get("name") == "research"][0]
        handler = research_call[1]["handler"]
        result = handler("python asyncio")
        assert "Research completed" in result
        assert (tmp_path / "session_research.json").exists()

    def test_cmd_verify_ok(self, tmp_path: Path) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "research_id": "RSCH-12345",
                }
            )
        )
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_command.call_args_list
        verify_call = [c for c in calls if c[1].get("name") == "verify"][0]
        handler = verify_call[1]["handler"]
        result = handler()
        assert "[MARU]" in result

    def test_cmd_verify_fail(self) -> None:
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_command.call_args_list
        verify_call = [c for c in calls if c[1].get("name") == "verify"][0]
        handler = verify_call[1]["handler"]
        result = handler()
        assert "[MARU-RESEARCH-GATE]" in result

    def test_cli_status_json(self, tmp_path: Path, capsys: Any) -> None:
        session = tmp_path / "session_research.json"
        session.write_text(
            json.dumps(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "research_id": "RSCH-12345",
                }
            )
        )
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_cli_command.call_args_list
        cli_call = calls[0]
        handler = cli_call[1]["handler_fn"]
        args = MagicMock()
        args.json = True
        assert handler(args) == 0
        captured = capsys.readouterr()
        assert "research_complete" in captured.out

    def test_cli_status_plain(self, tmp_path: Path, capsys: Any) -> None:
        ctx = MagicMock()
        register(ctx)
        calls = ctx.register_cli_command.call_args_list
        cli_call = calls[0]
        handler = cli_call[1]["handler_fn"]
        args = MagicMock()
        args.json = False
        assert handler(args) == 0
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.out or "OK" in captured.out
