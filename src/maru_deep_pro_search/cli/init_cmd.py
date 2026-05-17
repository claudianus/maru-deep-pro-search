"""`maru-deep-pro-search init` — Initialize project-local maru harness data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..harness.project import init_project


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"


def main(argv: list[str] | None = None) -> int:
    """Create `.maru/` (knowledge DB, harness.yaml) in a repo — no agent dotfiles here.

    MCP + Claude/Cursor/Copilot 등 에이전트 설정은 **사용자 전역**에만 둡니다.
    한 번 실행: ``maru-deep-pro-search setup`` (각 개발 머신에서).
    """
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search init",
        description=(
            "이 저장소에 .maru/ 하네스만 만듭니다 (knowledge.db, harness.yaml). "
            "에이전트(MCP·규칙)는 저장소에 쓰지 않습니다 — "
            "`maru-deep-pro-search setup`으로 각 머신 전역에 설정하세요."
        ),
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--no-agents-md",
        action="store_true",
        help="Skip creating AGENTS.md (project contributor hints)",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Skip updating .gitignore",
    )

    args = parser.parse_args(argv)

    print(f"\n🚀 Initializing maru harness at {Path(args.path).resolve()}\n")

    result = init_project(
        path=args.path,
        create_agents_md=not args.no_agents_md,
        create_gitignore=not args.no_gitignore,
    )

    for created in result["created"]:
        print(f"  {_green('✓')} {created}")

    print(f"\n{_green('✅ Harness initialized!')}")
    print(f"   Knowledge store: {Path(result['root']) / '.maru' / 'knowledge.db'}")
    print(
        f"   {_bold('에이전트(MCP·규칙·스킬):')} 이 머신에서 "
        f"`maru-deep-pro-search setup` 실행 (저장소 밖 전역 경로에만 기록됩니다)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
