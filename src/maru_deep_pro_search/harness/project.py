"""Project-level harness initialization."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .persistence import KnowledgeStore

logger = logging.getLogger("maru_deep_pro_search.harness.project")

DEFAULT_AGENTS_MD = """# Agent Instructions

> This project uses **maru-deep-pro-search** harness for research-first development.

## Rule Zero

**NEVER write code based solely on training data.**

Your training knowledge has a cutoff date. Libraries evolve. APIs change.
Always call `deep_research(query)` BEFORE making technical decisions.

## Tool Priority

1. `deep_research` — ALWAYS start here
2. `answer` — Quick factual checks
3. `parallel_search` — Multiple angles simultaneously
4. `fetch_page` / `fetch_bulk` — Read specific URLs
5. `stealthy_fetch` — Last resort for blocked sites

## Knowledge Cache

This project has a local knowledge store at `.maru/knowledge.db`.
Previous research results are cached and reused when relevant.

## Research Checklist

Before writing ANY code:
- [ ] Called `deep_research` on the topic
- [ ] Verified library versions are current
- [ ] Checked for known security issues
- [ ] Confirmed API signatures match latest docs
- [ ] Cited sources with [1], [2] in your answer
"""

DEFAULT_GITIGNORE = """# Maru Harness
.maru/knowledge.db
.maru/knowledge.db-journal
.maru/receipts/
.maru/*.bak
"""


def init_project(
    path: Path | str = ".",
    agents: list[str] | None = None,
    create_agents_md: bool = True,
    create_gitignore: bool = True,
    create_harness_yaml: bool = True,
) -> dict[str, Any]:
    """Initialize a project with the maru harness.

    Creates:
        .maru/knowledge.db   — local knowledge cache
        .maru/harness.yaml   — declarative harness spec (AHS)
        AGENTS.md            — project-specific agent instructions (if requested)
        .gitignore additions — exclude harness artifacts
        Agent-native configs — .claude/settings.json, .aider.conf.yml, etc.

    Args:
        path: Project root directory.
        agents: List of agent names to configure (e.g. ["cursor", "claude"]).
                If None, auto-detect installed agents.
        create_agents_md: Whether to create AGENTS.md.
        create_gitignore: Whether to append harness entries to .gitignore.
        create_harness_yaml: Whether to create `.maru/harness.yaml`.

    Returns:
        Summary dict with created paths and status.
    """
    root = Path(path).resolve()
    maru_dir = root / ".maru"
    maru_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []

    # 1. Knowledge store
    store = KnowledgeStore(db_path=maru_dir / "knowledge.db")
    store._connect()  # ensure schema exists
    created.append(str(maru_dir / "knowledge.db"))

    # 2. Harness Spec (.maru/harness.yaml)
    if create_harness_yaml:
        harness_yaml = maru_dir / "harness.yaml"
        if not harness_yaml.exists():
            from .spec import HarnessSpec

            spec = HarnessSpec.default()
            # Write a minimal readable YAML
            yaml_content = f"""# Agent Harness Specification (AHS) — maru-deep-pro-search
# This file declaratively defines how AI agents should behave in this project.
# The setup CLI translates this into agent-native config files.

mcp_servers:
  maru-deep-pro-search:
    command: python3
    args: [-m, maru_deep_pro_search.server]

research_protocol: |
{chr(10).join("  " + line for line in spec.research_protocol.splitlines())}

tool_priority:
{chr(10).join(f"  - {t}" for t in spec.tool_priority)}

commands:
{chr(10).join(f"  - name: {c.name}" + chr(10) + f"    description: {c.description}" + chr(10) + f"    prompt: {c.prompt}" for c in spec.commands)}

conventions:
{chr(10).join(f"  - {c}" for c in spec.conventions)}

knowledge_db_path: {spec.knowledge_db_path}
"""
            harness_yaml.write_text(yaml_content, encoding="utf-8")
            created.append(str(harness_yaml))

    # 3. AGENTS.md
    if create_agents_md:
        agents_md = root / "AGENTS.md"
        if not agents_md.exists():
            agents_md.write_text(DEFAULT_AGENTS_MD, encoding="utf-8")
            created.append(str(agents_md))

    # 4. .gitignore
    if create_gitignore:
        gitignore = root / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")
            if ".maru/knowledge.db" not in content:
                with gitignore.open("a", encoding="utf-8") as f:
                    f.write("\n" + DEFAULT_GITIGNORE + "\n")
                created.append(str(gitignore))
        else:
            gitignore.write_text(DEFAULT_GITIGNORE + "\n", encoding="utf-8")
            created.append(str(gitignore))

    # 5. Agent configs at project scope (agent-native files)
    if agents:
        from ..cli.setup import ADAPTER_REGISTRY

        for name in agents:
            adapter_cls = ADAPTER_REGISTRY.get(name)
            if adapter_cls:
                adapter = adapter_cls()  # type: ignore[abstract]
                adapter.configure(scope="project")
                logger.info("Configured %s for project scope", name)

    logger.info("Harness initialized at %s", root)
    return {
        "root": str(root),
        "created": created,
        "agents_configured": agents or [],
    }


class HarnessProject:
    """Accessor for a harness-enabled project."""

    def __init__(self, root: Path | str = ".") -> None:
        self.root = Path(root).resolve()
        self.maru_dir = self.root / ".maru"
        self._store: KnowledgeStore | None = None

    @property
    def store(self) -> KnowledgeStore:
        if self._store is None:
            self._store = KnowledgeStore(db_path=self.maru_dir / "knowledge.db")
        return self._store

    def is_initialized(self) -> bool:
        return (self.maru_dir / "knowledge.db").exists()
