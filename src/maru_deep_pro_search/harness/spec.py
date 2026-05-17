"""Agent Harness Specification (AHS) — declarative harness manifest.

Each agent has its own configuration dialect. AHS abstracts them into a
single declarative spec that the setup CLI translates to agent-native
configs (`.claude/settings.json`, `.aider.conf.yml`, `.cursorrules`, etc.).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LifecycleHook:
    """An event-driven hook fired at a specific lifecycle point."""

    event: str  # e.g. "post_tool_use", "pre_research", "post_write"
    matcher: str  # e.g. "Write|Edit", "deep_research", "*"
    action: str  # "command" | "prompt"
    command: str = ""  # shell command when action=="command"
    prompt: str = ""  # prompt text when action=="prompt"


@dataclass
class AgentCommand:
    """A custom slash command exposed to the agent."""

    name: str  # e.g. "research"
    description: str
    prompt: str  # what to send to the model when invoked


@dataclass
class AgentRule:
    """A path-based or global rule (like `.claude/rules/` or `.cursorrules`)."""

    scope: str  # "global" | path glob e.g. "src/**/*.py"
    content: str  # the rule text


@dataclass
class QualityGate:
    """Quality gate configuration (lint/format/type-check)."""

    language: str  # e.g. "python", "typescript"
    lint_cmd: str = ""
    test_cmd: str = ""
    format_cmd: str = ""


@dataclass
class HarnessSpec:
    """Declarative spec read from a project's ``.maru/harness.yaml``.

    The ``setup`` / ``sync`` CLI reads this from the **current working directory**
    and translates it into **user-global** agent-native configs (``~/.claude/``, etc.).
    """

    # ── MCP server registration ─────────────────────────────────
    mcp_servers: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ── Research-first enforcement ──────────────────────────────
    research_protocol: str = ""  # injected into agent system prompt / rules
    tool_priority: list[str] = field(default_factory=list)

    # ── Custom commands / skills ────────────────────────────────
    commands: list[AgentCommand] = field(default_factory=list)

    # ── Rules (path-based or global) ────────────────────────────
    rules: list[AgentRule] = field(default_factory=list)

    # ── Lifecycle hooks ─────────────────────────────────────────
    hooks: list[LifecycleHook] = field(default_factory=list)

    # ── Quality gates ───────────────────────────────────────────
    quality_gates: list[QualityGate] = field(default_factory=list)

    # ── Conventions / standards ─────────────────────────────────
    conventions: list[str] = field(default_factory=list)  # file paths to read

    # ── Knowledge store ─────────────────────────────────────────
    knowledge_db_path: str = ".maru/knowledge.db"

    # ── Plugins ─────────────────────────────────────────────────
    plugins: list[str] = field(default_factory=list)  # plugin names to load

    @classmethod
    def from_project(cls, root: str = ".") -> HarnessSpec:
        """Load spec from `.maru/harness.yaml` or return defaults."""
        from pathlib import Path

        path = Path(root) / ".maru" / "harness.yaml"
        if path.exists():
            import yaml

            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return cls(**data)
        return cls.default()

    @classmethod
    def default(cls) -> HarnessSpec:
        """Return the default maru harness spec."""
        return cls(
            mcp_servers={
                "maru-deep-pro-search": {
                    "command": sys.executable,
                    "args": ["-m", "maru_deep_pro_search.server"],
                }
            },
            research_protocol="""
🔴 필수 리서치 프로토콜 — 절대 위반 금지

규칙 1: 일반 사실·시세·추천 → answer(query). 코드·보안·깊은 조사 → deep_research(query).
규칙 2: query에는 과거 연도를 포함하지 마라. 현재 연도 또는 "latest"만 사용.
규칙 3: 리서치 결과를 [1], [2] 형태로 인용해야 한다.
규칙 4: 추측 금지. 부족하면 refined query로 answer 또는 deep_research를 다시 호출.
규칙 5: 코드/라이브러리 질문은 최신 버전과 API를 확인한 후 코드 작성.
규칙 6: 너의 학습 데이터는 낡았다. 웹은 최신이다. answer/deep_research로 항상 검증.
""".strip(),
            tool_priority=[
                "answer",
                "deep_research",
                "parallel_search",
                "web_search",
                "fetch_page",
                "stealthy_fetch",
            ],
            commands=[
                AgentCommand(
                    name="research",
                    description="주제에 대해 딥 리서치를 실행하고 인용된 답변을 받습니다.",
                    prompt="Call answer for general questions or deep_research for technical work; return a cited summary.",
                ),
                AgentCommand(
                    name="verify",
                    description="최근 작성한 코드가 리서치 결과와 일치하는지 확인합니다.",
                    prompt="Review the last code written against the research results in the knowledge store. Check API versions, citations, and security.",
                ),
            ],
            hooks=[
                LifecycleHook(
                    event="post_tool_use",
                    matcher="Write|Edit",
                    action="prompt",
                    prompt="The user just wrote/edited code. Verify citations [1], [2]. If missing, prompt answer or deep_research first.",
                ),
            ],
            quality_gates=[
                QualityGate(
                    language="python",
                    lint_cmd="python -m py_compile",
                ),
            ],
            conventions=["AGENTS.md"],
        )

    def to_agent_config(self, agent: str) -> dict[str, Any]:
        """Translate AHS to agent-native configuration dict."""
        if agent == "claude":
            return self._to_claude()
        if agent == "aider":
            return self._to_aider()
        if agent == "cursor":
            return self._to_cursor()
        if agent == "copilot":
            return self._to_copilot()
        return {}

    # ── translators ─────────────────────────────────────────────

    def _to_claude(self) -> dict[str, Any]:
        hooks_cfg: dict[str, list[dict]] = {"PostToolUse": []}
        for h in self.hooks:
            if h.event == "post_tool_use":
                hooks_cfg["PostToolUse"].append(
                    {
                        "matcher": h.matcher,
                        "hooks": [{"type": h.action, "command": h.command or h.prompt}],
                    }
                )
        return {
            "mcpServers": self.mcp_servers,
            "settings": {
                "hooks": hooks_cfg,
            },
            "commands": [
                {"name": c.name, "description": c.description, "prompt": c.prompt}
                for c in self.commands
            ],
            "rules": [{"scope": r.scope, "content": r.content} for r in self.rules],
            "claude_md": self.research_protocol,
        }

    def _to_aider(self) -> dict[str, Any]:
        return {
            "read": self.conventions,
            "auto_lint": any(q.lint_cmd for q in self.quality_gates),
            "lint_cmd": [f"{q.language}: {q.lint_cmd}" for q in self.quality_gates if q.lint_cmd],
            "auto_test": any(q.test_cmd for q in self.quality_gates),
            "test_cmd": [f"{q.language}: {q.test_cmd}" for q in self.quality_gates if q.test_cmd],
            "conventions_md": self.research_protocol,
        }

    def _to_cursor(self) -> dict[str, Any]:
        return {
            "mcpServers": self.mcp_servers,
            "rules": self.research_protocol,
            "commands": [
                {"name": c.name, "description": c.description, "prompt": c.prompt}
                for c in self.commands
            ],
        }

    def _to_copilot(self) -> dict[str, Any]:
        return {
            "instructions": self.research_protocol,
            "mcpServers": self.mcp_servers,
        }
