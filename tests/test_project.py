"""Tests for harness project initialization."""

from __future__ import annotations

from maru_deep_pro_search.harness.project import HarnessProject, init_project


class TestInitProject:
    def test_creates_knowledge_db(self, tmp_path):
        result = init_project(path=tmp_path, create_agents_md=False, create_gitignore=False)
        assert (tmp_path / ".maru" / "knowledge.db").exists()
        assert "knowledge.db" in result["created"][0]

    def test_creates_agents_md(self, tmp_path):
        result = init_project(path=tmp_path, create_agents_md=True, create_gitignore=False)
        assert (tmp_path / "AGENTS.md").exists()
        assert any("AGENTS.md" in c for c in result["created"])

    def test_skips_existing_agents_md(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("existing")
        result = init_project(path=tmp_path, create_agents_md=True, create_gitignore=False)
        assert (tmp_path / "AGENTS.md").read_text() == "existing"
        assert not any("AGENTS.md" in c for c in result["created"])

    def test_appends_to_gitignore(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")
        result = init_project(path=tmp_path, create_agents_md=False, create_gitignore=True)
        content = gitignore.read_text()
        assert ".maru/knowledge.db" in content
        assert "*.pyc" in content
        assert any(".gitignore" in c for c in result["created"])

    def test_skips_gitignore_if_already_has_maru(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".maru/knowledge.db\n")
        result = init_project(path=tmp_path, create_agents_md=False, create_gitignore=True)
        assert not any(".gitignore" in c for c in result["created"])

    def test_creates_gitignore_if_missing(self, tmp_path):
        result = init_project(path=tmp_path, create_agents_md=False, create_gitignore=True)
        assert (tmp_path / ".gitignore").exists()
        assert ".maru/knowledge.db" in (tmp_path / ".gitignore").read_text()

    def test_creates_harness_yaml(self, tmp_path):
        result = init_project(path=tmp_path, create_agents_md=False, create_gitignore=False)
        assert (tmp_path / ".maru" / "harness.yaml").exists()

    def test_skips_harness_yaml_if_exists(self, tmp_path):
        harness = tmp_path / ".maru" / "harness.yaml"
        harness.parent.mkdir(parents=True, exist_ok=True)
        harness.write_text("existing")
        result = init_project(path=tmp_path, create_agents_md=False, create_gitignore=False)
        assert harness.read_text() == "existing"
        assert not any("harness.yaml" in c for c in result["created"])

    def test_with_agent_config(self, monkeypatch, tmp_path):
        # Mock the adapter registry to avoid real agent setup
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.setup.ADAPTER_REGISTRY",
            {"mock": type("MockAdapter", (), {
                "__init__": lambda self: None,
                "configure": lambda self, scope: None,
            })},
        )
        result = init_project(
            path=tmp_path, agents=["mock"], create_agents_md=False, create_gitignore=False
        )
        assert "mock" in result["agents_configured"]

    def test_with_unknown_agent(self, monkeypatch, tmp_path):
        result = init_project(
            path=tmp_path, agents=["unknown"], create_agents_md=False, create_gitignore=False
        )
        assert "unknown" in result["agents_configured"]


class TestHarnessProject:
    def test_is_initialized(self, tmp_path):
        init_project(path=tmp_path, create_agents_md=False, create_gitignore=False)
        hp = HarnessProject(tmp_path)
        assert hp.is_initialized() is True

    def test_store_lazy_load(self, tmp_path):
        init_project(path=tmp_path, create_agents_md=False, create_gitignore=False)
        hp = HarnessProject(tmp_path)
        store1 = hp.store
        store2 = hp.store
        assert store1 is store2  # cached
