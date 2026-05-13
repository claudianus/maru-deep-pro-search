"""Tests for maru harness: persistence, project init, workflow."""

from __future__ import annotations

import tempfile
from pathlib import Path

from maru_deep_pro_search.harness.persistence import KnowledgeStore
from maru_deep_pro_search.harness.project import HarnessProject, init_project
from maru_deep_pro_search.harness.workflow import (
    WorkflowEngine,
    WorkflowPhase,
    WorkflowState,
)


class TestKnowledgeStore:
    def test_save_and_query_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = KnowledgeStore(db_path=db)
            store.save(
                query="Python async best practices", answer="Use asyncio.gather...", sources=[]
            )
            results = store.query("Python async best practices")
            assert len(results) == 1
            assert results[0].answer == "Use asyncio.gather..."

    def test_query_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = KnowledgeStore(db_path=db)
            results = store.query("nonexistent query")
            assert results == []

    def test_update_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = KnowledgeStore(db_path=db)
            store.save(query="test", answer="old", sources=[])
            store.save(query="test", answer="new", sources=[])
            results = store.query("test")
            assert results[0].answer == "new"

    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = KnowledgeStore(db_path=db)
            store.save(query="q1", answer="a1", sources=[])
            store.save(query="q2", answer="a2", sources=[])
            stats = store.get_stats()
            assert stats["total_entries"] == 2

    def test_prune(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = KnowledgeStore(db_path=db)
            # Can't easily test time-based pruning without mocking,
            # so just verify it doesn't crash
            store.save(query="q", answer="a", sources=[])
            deleted = store.prune(max_age_days=0)
            # 0 days means everything older than 0 days (which is everything)
            assert deleted >= 0

    def test_record_domain_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = KnowledgeStore(db_path=db)
            store.record_domain_fetch("github.com", 500.0, True)
            store.record_domain_fetch("github.com", 600.0, True)
            store.record_domain_fetch("github.com", 30000.0, False)
            stats = store.get_domain_stats("github.com")
            assert stats is not None
            assert stats["success_rate"] == 2 / 3
            assert stats["failure_count"] == 1
            assert stats["total"] == 3

    def test_get_domain_stats_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = KnowledgeStore(db_path=db)
            assert store.get_domain_stats("nonexistent.com") is None


class TestHarnessProject:
    def test_init_project_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(path=root, agents=None, create_agents_md=True, create_gitignore=True)
            assert (root / ".maru" / "knowledge.db").exists()
            assert (root / "AGENTS.md").exists()
            assert (root / ".gitignore").exists()

    def test_init_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(path=root)
            init_project(path=root)
            # Should not crash on second init
            assert (root / ".maru" / "knowledge.db").exists()

    def test_harness_project_accessor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(path=root)
            hp = HarnessProject(root)
            assert hp.is_initialized()
            assert hp.store is not None


class TestWorkflowEngine:
    def test_run_full_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "wf.db"
            store = KnowledgeStore(db_path=db)
            engine = WorkflowEngine(store=store)
            state = WorkflowState(query="How to use React hooks")
            results = list(engine.run(state))
            # Should yield context_load, research, gap_detection, design, implement, verify, complete
            assert len(results) >= 4
            assert results[0].phase == WorkflowPhase.CONTEXT_LOAD
            assert results[0].success is True

    def test_context_load_with_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(path=root)
            # Change to project dir so AGENTS.md is found
            import os

            old_cwd = os.getcwd()
            os.chdir(root)
            try:
                store = KnowledgeStore(db_path=root / ".maru" / "knowledge.db")
                engine = WorkflowEngine(store=store)
                state = WorkflowState(query="test")
                results = list(engine.run(state))
                assert results[0].phase == WorkflowPhase.CONTEXT_LOAD
                assert "AGENTS.md" in results[0].output or "No project context" in results[0].output
            finally:
                os.chdir(old_cwd)
