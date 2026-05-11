"""`maru-deep-pro-search init` — Initialize project harness."""

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
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search init",
        description="Initialize maru harness in the current project.",
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=[
            "claude", "cursor", "kimi", "windsurf", "antigravity", "kilo", "opencode",
            "aider", "copilot", "continue", "cline", "zed", "jetbrains",
            "supermaven", "cody", "codeium", "amazon_q", "devin", "tabnine",
        ],
        help="Agents to configure at project scope",
    )
    parser.add_argument(
        "--no-agents-md",
        action="store_true",
        help="Skip creating AGENTS.md",
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
        agents=args.agents,
        create_agents_md=not args.no_agents_md,
        create_gitignore=not args.no_gitignore,
    )

    for created in result["created"]:
        print(f"  {_green('✓')} {created}")

    if args.agents:
        print(f"\n  {_green('✓')} Agents configured: {', '.join(args.agents)}")

    print(f"\n{_green('✅ Harness initialized!')}")
    print(f"   Knowledge store: {Path(result['root']) / '.maru' / 'knowledge.db'}")
    print("   Next: commit changes and restart your agent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
