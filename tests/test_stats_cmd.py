"""Tests for stats CLI command."""

from __future__ import annotations

import tempfile
from pathlib import Path

from maru_deep_pro_search.cli.stats_cmd import cmd_stats, main


class TestCmdStats:
    def test_empty_db(self, tmp_path):
        db = tmp_path / "knowledge.db"
        args = type("Args", (), {"db": str(db)})()
        assert cmd_stats(args) == 0

    def test_with_entries(self, tmp_path):
        from maru_deep_pro_search.harness.persistence import KnowledgeStore
        db = tmp_path / "knowledge.db"
        store = KnowledgeStore(db)
        store.save(query="python asyncio", answer="use gather", sources=[])
        store.save(query="rust ownership", answer="use borrow", sources=[])
        store.record_domain_fetch("github.com", 500.0, True)
        args = type("Args", (), {"db": str(db)})()
        assert cmd_stats(args) == 0

    def test_default_db_path(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from maru_deep_pro_search.harness.persistence import KnowledgeStore
        db = KnowledgeStore._default_db_path()
        store = KnowledgeStore(db)
        store.save(query="test", answer="answer", sources=[])
        args = type("Args", (), {"db": None})()
        assert cmd_stats(args) == 0

    def test_error_handling(self, tmp_path):
        # Pass a non-database file to trigger error
        bad = tmp_path / "notadb.txt"
        bad.write_text("hello")
        args = type("Args", (), {"db": str(bad)})()
        assert cmd_stats(args) == 1


class TestMain:
    def test_main_with_db(self, tmp_path):
        db = tmp_path / "knowledge.db"
        assert main(["--db", str(db)]) == 0

    def test_main_default(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0
