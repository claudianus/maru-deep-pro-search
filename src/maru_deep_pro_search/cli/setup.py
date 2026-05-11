"""Main entry point for `maru-deep-pro-search setup` CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .detect import detect_agents, installed_agents
from .env_check import (
    bold,
    ensure_compatible_python,
    green,
    red,
    yellow,
)
from .agents.claude import ClaudeAdapter
from .agents.cursor import CursorAdapter
from .agents.kimi import KimiAdapter
from .agents.antigravity import AntiGravityAdapter
from .agents.kilo import KiloAdapter
from .agents.opencode import OpenCodeAdapter
from .agents.windsurf import WindsurfAdapter
from .agents.aider import AiderAdapter
from .agents.copilot import CopilotAdapter
from .agents.continue_ import ContinueAdapter
from .agents.cline import ClineAdapter
from .agents.zed import ZedAdapter
from .agents.jetbrains import JetBrainsAdapter
from .agents.supermaven import SupermavenAdapter
from .agents.cody import CodyAdapter
from .agents.codeium import CodeiumAdapter
from .agents.amazon_q import AmazonQAdapter
from .agents.devin import DevinAdapter
from .agents.tabnine import TabnineAdapter

ADAPTER_REGISTRY = {
    "claude": ClaudeAdapter,
    "cursor": CursorAdapter,
    "kimi": KimiAdapter,
    "antigravity": AntiGravityAdapter,
    "kilo": KiloAdapter,
    "opencode": OpenCodeAdapter,
    "windsurf": WindsurfAdapter,
    "aider": AiderAdapter,
    "copilot": CopilotAdapter,
    "continue": ContinueAdapter,
    "cline": ClineAdapter,
    "zed": ZedAdapter,
    "jetbrains": JetBrainsAdapter,
    "supermaven": SupermavenAdapter,
    "cody": CodyAdapter,
    "codeium": CodeiumAdapter,
    "amazon_q": AmazonQAdapter,
    "devin": DevinAdapter,
    "tabnine": TabnineAdapter,
}


def cmd_list(args: argparse.Namespace) -> int:
    """Show detected agents and their installation status."""
    print("\n🔍 설치된 AI 에이전트 감지 중...\n")
    agents = detect_agents()
    for name, detected in agents.items():
        adapter_cls = ADAPTER_REGISTRY[name]
        display = adapter_cls.display_name
        if detected:
            print(f"  {green('✓')} {display} ({name})")
        else:
            print(f"  {red('✗')} {display} ({name})")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    """Run the interactive setup for selected agents."""
    print("\n🔍 설치된 AI 에이전트 감지 중...\n")
    agents = detect_agents()
    installed = [name for name, detected in agents.items() if detected]

    if not installed:
        print(yellow("  설치된 에이전트를 찾을 수 없습니다."))
        print("  지원하는 에이전트: Claude Code, Cursor, Kimi, AntiGravity, Kilo Code, OpenCode, Windsurf")
        return 1

    # If --agents is not provided, use all detected agents
    selected = args.agents if args.agents else installed

    # Filter to only installed agents
    selected = [s for s in selected if s in installed]
    if not selected:
        print(red("  선택한 에이전트 중 설치된 것이 없습니다."))
        return 1

    scope = args.scope or "user"

    print(f"\n{bold('설정할 에이전트:')} {', '.join(selected)}")
    print(f"{bold('설정 범위:')} {scope}\n")

    for name in selected:
        adapter_cls = ADAPTER_REGISTRY[name]
        adapter = adapter_cls()
        print(f"⚙️  {adapter.display_name} 설정 중...")

        result = adapter.configure(scope=scope)

        if result["backups"]:
            for b in result["backups"]:
                print(f"   ✓ 백업 저장: {b}")
        if result["mcp_installed"]:
            print(f"   ✓ MCP 서버 등록 완료")
        else:
            print(f"   {yellow('! MCP 서버 등록 실패')}")
        if result["rules_injected"]:
            print(f"   ✓ 리서치 프로토콜 주입 완료")
        else:
            print(f"   {yellow('! 규칙 주입 실패 (수동 설정 필요)')}")

    # Semantic search recommendation
    try:
        import sentence_transformers
        print(f"\n  {green('✓')} semantic search (sentence-transformers) 설치됨")
    except ImportError:
        print(f"\n  {yellow('!')} semantic search 미설치")
        print(f"     설치 시 검색 품질 ↑: {bold('pip install sentence-transformers')}")
        print(f"     또는: {bold('pip install maru-deep-pro-search[semantic]')}")

    print(f"\n{green('✅ 완료!')} 에이전트를 재시작하면 적용됩니다.")
    print(f"   되돌리려면: {bold('maru-deep-pro-search setup --restore')}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """Restore agent configs from backups."""
    print("\n🔄 설정 복원 중...\n")
    restored_any = False
    for name, adapter_cls in ADAPTER_REGISTRY.items():
        adapter = adapter_cls()
        if adapter.detect():
            if adapter.restore():
                print(f"   ✓ {adapter.display_name} 복원 완료")
                restored_any = True
            else:
                print(f"   ✗ {adapter.display_name} 복원할 백업 없음")

    if restored_any:
        print(f"\n{_green('✅ 복원 완료!')} 에이전트를 재시작하세요.")
    else:
        print(yellow("복원할 백업을 찾을 수 없습니다."))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Verify that configs are still in place."""
    print("\n🔍 설정 상태 확인 중...\n")
    all_ok = True
    for name, adapter_cls in ADAPTER_REGISTRY.items():
        adapter = adapter_cls()
        if adapter.detect():
            # Simple heuristic: check if MCP config exists
            mcp_ok = adapter.install_mcp(scope="user")  # idempotent
            print(f"   {'✓' if mcp_ok else '✗'} {adapter.display_name}")
            if not mcp_ok:
                all_ok = False
    return 0 if all_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search",
        description="One-click setup for maru-deep-pro-search across AI agents.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup command (default)
    setup_parser = subparsers.add_parser("setup", help="Configure AI agents")
    setup_parser.add_argument(
        "--agents",
        nargs="+",
        choices=list(ADAPTER_REGISTRY.keys()),
        help="Specific agents to configure (default: auto-detected)",
    )
    setup_parser.add_argument(
        "--scope",
        choices=["user", "project"],
        default="user",
        help="Configuration scope",
    )
    setup_parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore previous backups",
    )
    setup_parser.add_argument(
        "--list",
        action="store_true",
        help="List detected agents",
    )
    setup_parser.add_argument(
        "--check",
        action="store_true",
        help="Check configuration status",
    )

    args = parser.parse_args(argv)

    # Always validate Python version first — never let the user stumble
    # into a cryptic pip error later on.
    if ensure_compatible_python() != 0:
        return 1

    if args.command == "setup":
        if args.list:
            return cmd_list(args)
        if args.restore:
            return cmd_restore(args)
        if args.check:
            return cmd_check(args)
        return cmd_setup(args)

    # Default: run setup if no subcommand given
    return cmd_setup(args)


if __name__ == "__main__":
    sys.exit(main())
