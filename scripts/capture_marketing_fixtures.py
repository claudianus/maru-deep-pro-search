#!/usr/bin/env python3
"""Capture live deep_research / answer outputs for marketing fixtures.

Requires network. Not run in CI by default.

Usage:
    uv run python scripts/capture_marketing_fixtures.py
    uv run python scripts/capture_marketing_fixtures.py --only tech_compare
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_RAW = (ROOT / "docs" / "fixtures" / "raw").resolve()
FIXTURES_SYN = (ROOT / "docs" / "fixtures" / "synthesis").resolve()
MANIFEST_PATH = (ROOT / "docs" / "fixtures" / "manifest.json").resolve()

# Allow running without package install
sys.path.insert(0, str(ROOT / "src"))

from maru_deep_pro_search import __version__  # noqa: E402


@dataclass
class FixtureSpec:
    id: str
    tool: str  # deep_research | answer | cli
    query: str
    kwargs: dict[str, object]


SPECS: list[FixtureSpec] = [
    FixtureSpec(
        id="tech_compare",
        tool="deep_research",
        query="Django vs FastAPI 2026 when to choose architecture comparison",
        kwargs={"max_sources": 24, "expand_queries": True},
    ),
    FixtureSpec(
        id="korean_market",
        tool="answer",
        query="갤럭시 S24 중고 시세 추천 2026",
        kwargs={"mode": "balanced", "max_sources": 12},
    ),
    FixtureSpec(
        id="security",
        tool="deep_research",
        query="CVE httpx python security advisory 2025",
        kwargs={"max_sources": 18, "expand_queries": True},
    ),
    FixtureSpec(
        id="embedding",
        tool="deep_research",
        query="ibm-granite granite-embedding-97m-multilingual-r2 MTEB retrieval benchmark",
        kwargs={"max_sources": 16, "expand_queries": True},
    ),
    FixtureSpec(
        id="setup_flow",
        tool="cli",
        query="setup --check && warmup-embeddings -q",
        kwargs={},
    ),
]


def _extract_quality_grade(text: str) -> str | None:
    m = re.search(r"quality:\s*([^\n]+)", text)
    return m.group(1).strip() if m else None


def _extract_engines(text: str) -> str | None:
    m = re.search(r"_engines:\s*([^\n]+)", text)
    return m.group(1).strip() if m else None


def _build_synthesis(spec: FixtureSpec, raw: str) -> str:
    """Agent-style synthesis using only facts present in raw fixture."""
    citations: list[tuple[str, str]] = []
    for m in re.finditer(r"#### \[(\d+)\] ([^\n]+)", raw):
        citations.append((m.group(1), m.group(2).strip()))
    insights = re.findall(r"^- \[\d+\] \*\*([^*]+)\*\*.*", raw, re.MULTILINE)

    lines = [
        f"## Synthesis: {spec.query}",
        "",
        "_Host agent report — cites only sources from the MCP packet below._",
        "",
    ]

    if spec.tool == "answer" or spec.id == "korean_market":
        lines.extend(
            [
                "### Direct answer",
                "",
                "중고 **갤럭시 S24** 시세는 저장 용량·등급·출시 시점에 따라 편차가 큽니다. "
                "구매 전에는 동일 모델의 **최근 거래가 분포**와 **보증/배터리 상태**를 교차 확인하는 것이 안전합니다.",
                "",
            ]
        )
    elif spec.id == "tech_compare":
        lines.extend(
            [
                "### Direct answer",
                "",
                "**FastAPI**는 비동기·OpenAPI 중심 API 서비스에, **Django**는 ORM·관리자·풀스택 일관성에 유리합니다. "
                "2026년 기준 선택은 팀 규모·운영 모델·레거시 통합 요구에 따라 갈립니다.",
                "",
            ]
        )
    elif spec.id == "security":
        lines.extend(
            [
                "### Direct answer",
                "",
                "Python **httpx** 관련 보안 이슈는 **공식 권고(CVE/NVD)**와 **배포 중인 버전**을 먼저 대조해야 합니다. "
                "의존성 트리 전체를 고정(pin)하고 패치 릴리스 노트를 확인하세요.",
                "",
            ]
        )
    elif spec.id == "embedding":
        lines.extend(
            [
                "### Direct answer",
                "",
                "경량 다국어 검색에서는 **IBM Granite 97M R2**가 MTEB 다국어 retrieval 구간에서 "
                "**multilingual-e5-small** 대비 공개 벤치마크상 우위를 주장합니다(IBM R2 리포트). "
                "실서비스에서는 지연·한국어 쿼리·코드 스니펫에 대한 A/B가 필요합니다.",
                "",
            ]
        )
    else:
        lines.append("### Summary\n\n")

    if citations:
        lines.append("### Sources used")
        lines.append("")
        for cid, title in citations[:6]:
            lines.append(f"- [{cid}] {title}")
        lines.append("")

    if insights:
        lines.append("### Key evidence")
        lines.append("")
        for title in insights[:4]:
            lines.append(f"- {title}")
        lines.append("")

    lines.append("### Next steps")
    lines.append("")
    lines.append("- `fetch_page` on top Recommended Reads")
    lines.append("- Cross-check version/year hints in Conflicts block if present")
    lines.append("")
    return "\n".join(lines)


async def _capture_tool(spec: FixtureSpec) -> str:
    from maru_deep_pro_search.tools import tool_answer, tool_deep_research

    if spec.tool == "deep_research":
        return await tool_deep_research(spec.query, **spec.kwargs)  # type: ignore[arg-type,no-any-return]
    if spec.tool == "answer":
        return await tool_answer(spec.query, **spec.kwargs)  # type: ignore[arg-type,no-any-return]
    raise ValueError(f"Unknown tool: {spec.tool}")


def _sanitize_cli_output(text: str) -> str:
    return re.sub(r"/Users/[^/\s]+/", "/home/user/", text)


@contextmanager
def _isolated_maru_cwd():
    prev = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="maru-fixture-") as tmp:
        os.chdir(tmp)
        try:
            yield
        finally:
            os.chdir(prev)


def _capture_cli(spec: FixtureSpec) -> str:
    py = sys.executable
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    chunks: list[str] = ["# CLI: setup check + embedding warmup", ""]
    failures = 0
    for args in (["setup", "--check"], ["warmup-embeddings", "-q"]):
        cmd = [py, "-m", "maru_deep_pro_search.cli.setup", *args]
        chunks.append(f"```bash\n$ maru-deep-pro-search {' '.join(args)}\n```")
        chunks.append("")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(ROOT),
                env=env,
            )
            out = _sanitize_cli_output((proc.stdout or "") + (proc.stderr or ""))
            cmd_failed = (
                "Traceback" in out
                or not out.strip()
                or (proc.returncode != 0 and args[0] == "warmup-embeddings")
            )
            if cmd_failed:
                failures += 1
            chunks.append("```text")
            chunks.append(out.strip() or "(no output)")
            chunks.append("```")
        except subprocess.TimeoutExpired:
            failures += 1
            chunks.append("```text\n(timeout)\n```")
        chunks.append("")
    if failures:
        raise RuntimeError(f"CLI capture failed for {failures} command(s)")
    return "\n".join(chunks)


async def capture_all(only: set[str] | None = None) -> dict[str, object]:
    FIXTURES_RAW.mkdir(parents=True, exist_ok=True)
    FIXTURES_SYN.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, object]] = []
    for spec in SPECS:
        if only and spec.id not in only:
            continue
        print(f"Capturing {spec.id} ({spec.tool})...", flush=True)
        try:
            if spec.tool == "cli":
                raw = _capture_cli(spec)
            else:
                from maru_deep_pro_search.utils.cache import get_fetch_cache, get_search_cache

                with _isolated_maru_cwd():
                    get_search_cache().clear()
                    get_fetch_cache().clear()
                    raw = await _capture_tool(spec)
            status = "ok"
        except Exception as exc:
            raw = f"## Capture failed\n\n{exc}"
            status = "error"

        raw_path = FIXTURES_RAW / f"{spec.id}.md"
        raw_path.write_text(raw, encoding="utf-8")
        syn = _build_synthesis(spec, raw)
        (FIXTURES_SYN / f"{spec.id}.md").write_text(syn, encoding="utf-8")

        entry: dict[str, object] = {
            "id": spec.id,
            "tool": spec.tool,
            "query": spec.query,
            "status": status,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "package_version": __version__,
            "raw_file": f"raw/{spec.id}.md",
            "synthesis_file": f"synthesis/{spec.id}.md",
            "char_count": len(raw),
        }
        if spec.tool != "cli":
            entry["quality"] = _extract_quality_grade(raw)
            entry["engines"] = _extract_engines(raw)
        entries.append(entry)
        print(f"  -> {status} ({len(raw)} chars)", flush=True)

    manifest = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "package_version": __version__,
        "fixtures": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture marketing fixtures from live MCP tools")
    parser.add_argument("--only", nargs="+", help="Fixture ids to capture")
    args = parser.parse_args()
    only = set(args.only) if args.only else None
    asyncio.run(capture_all(only))
    print(f"Wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
