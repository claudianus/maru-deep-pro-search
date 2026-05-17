"""Main entry point for `maru-deep-pro-search setup` CLI."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from .agents.aider import AiderAdapter
from .agents.amazon_q import AmazonQAdapter
from .agents.antigravity import AntiGravityAdapter
from .agents.claude import ClaudeAdapter
from .agents.cline import ClineAdapter
from .agents.codeium import CodeiumAdapter
from .agents.codex import CodexAdapter
from .agents.cody import CodyAdapter
from .agents.continue_ import ContinueAdapter
from .agents.copilot import CopilotAdapter
from .agents.cursor import CursorAdapter
from .agents.devin import DevinAdapter
from .agents.hermes import HermesAdapter
from .agents.jetbrains import JetBrainsAdapter
from .agents.kilo import KiloAdapter
from .agents.kimi import KimiAdapter
from .agents.opencode import OpenCodeAdapter
from .agents.supermaven import SupermavenAdapter
from .agents.tabnine import TabnineAdapter
from .agents.windsurf import WindsurfAdapter
from .agents.zed import ZedAdapter
from .detect import detect_agents
from .env_check import (
    bold,
    ensure_compatible_python,
    green,
    red,
    yellow,
)

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
    "hermes": HermesAdapter,
    "codex": CodexAdapter,
}


_SENTENCE_TRANSFORMERS_SPEC = "sentence-transformers>=3.0.0"
_SENTENCE_TRANSFORMERS_PIP = f'"{_SENTENCE_TRANSFORMERS_SPEC}"'


def _pip_install_sentence_transformers() -> tuple[bool, str]:
    """Install *sentence-transformers* for the interpreter running this CLI.

    Order: ``python -m pip install`` → ``--user`` → ``uv pip`` targeting this
    executable → ``uv pip install --system`` (works without an active venv).

    Returns:
        ``(ok, detail)`` — *detail* is the successful shell command or a short
        error tail.
    """
    attempts: list[list[str]] = [
        [sys.executable, "-m", "pip", "install", _SENTENCE_TRANSFORMERS_SPEC],
        [sys.executable, "-m", "pip", "install", "--user", _SENTENCE_TRANSFORMERS_SPEC],
    ]
    uv_bin = shutil.which("uv")
    if uv_bin:
        attempts.extend(
            (
                [uv_bin, "pip", "install", "--python", sys.executable, _SENTENCE_TRANSFORMERS_SPEC],
                [uv_bin, "pip", "install", "--system", _SENTENCE_TRANSFORMERS_SPEC],
            )
        )

    last_msg = ""
    for cmd in attempts:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=900)
            return True, " ".join(cmd)
        except subprocess.TimeoutExpired as exc:
            last_msg = str(exc)
        except subprocess.CalledProcessError as exc:
            tail = (exc.stderr or exc.stdout or str(exc)).strip()
            last_msg = tail[-800:] if tail else str(exc)
        except OSError as exc:
            last_msg = str(exc)

    return False, last_msg


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
        print(
            "  지원하는 에이전트: Claude Code, Cursor, Kimi, AntiGravity, Kilo Code, OpenCode, Windsurf, Aider, Copilot, Continue, Cline, Zed, JetBrains, Supermaven, Cody, Codeium, Amazon Q, Devin, Tabnine, Hermes, Codex"
        )
        return 1

    # If --agents is not provided, use all detected agents
    selected = args.agents if args.agents else installed

    # Filter to only installed agents
    selected = [s for s in selected if s in installed]
    if not selected:
        print(red("  선택한 에이전트 중 설치된 것이 없습니다."))
        return 1

    scope = "user"

    print(f"\n{bold('설정할 에이전트:')} {', '.join(selected)}")
    print(
        f"{bold('설정 범위:')} {scope} (전역 — 홈 디렉터리 등, 이 저장소에 에이전트 점 파일을 만들지 않음)\n"
    )

    for name in selected:
        adapter_cls = ADAPTER_REGISTRY[name]
        adapter = adapter_cls()  # type: ignore[abstract]
        print(f"⚙️  {adapter.display_name} 설정 중...")

        result = adapter.configure(scope=scope)

        if result["backups"]:
            for b in result["backups"]:
                print(f"   ✓ 백업 저장: {b}")
        if result["mcp_installed"]:
            print("   ✓ MCP 서버 등록 완료")
        else:
            print(f"   {yellow('! MCP 서버 등록 실패')}")
        if result["rules_injected"]:
            print("   ✓ 리서치 프로토콜 주입 완료")
        else:
            print(f"   {yellow('! 규칙 주입 실패 (수동 설정 필요)')}")
        if result.get("skills_installed") is True:
            print("   ✓ SKILL.md 규칙 파일 설치 완료")
        elif result.get("skills_installed") is False:
            print(f"   {yellow('! SKILL.md 규칙 파일 설치 실패 (수동 설정 필요)')}")
        elif result.get("skills_supported") is False:
            print("   ℹ SKILL.md 규칙 파일 미지원")

    # Semantic search is useful but heavy. Keep default setup quiet and avoid
    # surprise model downloads in MCP stdio environments.
    import importlib.util

    if importlib.util.find_spec("sentence_transformers"):
        print(f"\n  {green('✓')} semantic search (sentence-transformers) 설치됨")
    elif os.environ.get("MARU_ENABLE_SEMANTIC_INSTALL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        print(f"\n  {yellow('!')} semantic search 미설치 — 자동 설치 시도 중...")
        ok, detail = _pip_install_sentence_transformers()
        if ok:
            print(f"     {green('✓')} sentence-transformers 설치 완료 ({detail})")
        else:
            print(f"     {yellow('!')} 자동 설치 실패")
            if detail:
                print(f"     {detail}")
            print(
                f"     수동: {bold(f'{sys.executable} -m pip install --user {_SENTENCE_TRANSFORMERS_PIP}')}"
            )
            print(f"     또는: {bold(f'uv pip install --system {_SENTENCE_TRANSFORMERS_PIP}')}")
            print(
                "     PyPI 패키지는 Python 3.10+ 필요: "
                + bold("python3.12 -m pip install 'maru-deep-pro-search[semantic]'")
            )
    else:
        print(f"\n  {yellow('!')} semantic search 미설치 — 기본 설정에서는 자동 설치하지 않음")
        print(f"     필요하면: {bold('MARU_ENABLE_SEMANTIC_INSTALL=1 maru-deep-pro-search setup')}")
        print(
            f"     수동: {bold(f'{sys.executable} -m pip install --user {_SENTENCE_TRANSFORMERS_PIP}')}"
        )

    print(f"\n{green('✅ 완료!')} 에이전트를 재시작하면 적용됩니다.")
    print(f"   되돌리려면: {bold('maru-deep-pro-search setup --restore')}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """Restore agent configs from backups."""
    print("\n🔄 설정 복원 중...\n")
    restored_any = False
    for _name, adapter_cls in ADAPTER_REGISTRY.items():
        adapter = adapter_cls()  # type: ignore[abstract]
        if adapter.detect():
            if adapter.restore():
                print(f"   ✓ {adapter.display_name} 복원 완료")
                restored_any = True
            else:
                print(f"   ✗ {adapter.display_name} 복원할 백업 없음")

    if restored_any:
        print(f"\n{green('✅ 복원 완료!')} 에이전트를 재시작하세요.")
    else:
        print(yellow("복원할 백업을 찾을 수 없습니다."))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Verify configs (read-only; does not modify files)."""
    from .doctor import diagnose_adapter, format_diagnosis_line

    print("\n🔍 설정 상태 확인 중 (읽기 전용)...\n")
    all_ok = True
    only = set(args.agents) if getattr(args, "agents", None) else None
    verified = 0
    for _name, adapter_cls in ADAPTER_REGISTRY.items():
        if only is not None and _name not in only:
            continue
        adapter = adapter_cls()  # type: ignore[abstract]
        if not adapter.detect():
            continue
        verified += 1
        diag = diagnose_adapter(adapter, scope="user")
        healthy, line = format_diagnosis_line(adapter.display_name, diag)
        print(f"   {line}")
        if not healthy:
            all_ok = False
    if only is not None and verified == 0:
        print(
            yellow(
                "선택한 에이전트가 이 환경에서 감지되지 않았습니다. "
                "`setup --list`로 감지 목록을 확인하세요."
            )
        )
        return 1
    if all_ok:
        print(f"\n{green('✅ 모든 감지된 에이전트 설정이 정상입니다.')}")
    else:
        print(
            f"\n{yellow('일부 항목에 문제가 있습니다.')} "
            f"{bold('maru-deep-pro-search setup --repair')} 로 자동 수리할 수 있습니다."
        )
    return 0 if all_ok else 1


def run_repair_after_update(*, repair_skills: bool = False) -> int:
    """Repair all detected agents (used by ``update --with-setup``)."""
    agents = detect_agents()
    installed = [name for name, detected in agents.items() if detected]
    if not installed:
        return 0
    ok_count = 0
    for name in installed:
        adapter = ADAPTER_REGISTRY[name]()  # type: ignore[abstract]
        result = adapter.configure(scope="user", repair=True, repair_skills=repair_skills)
        if result.get("success"):
            ok_count += 1
    return 0 if ok_count == len(installed) else 1


def cmd_repair(args: argparse.Namespace) -> int:
    """Repair agent configs: refresh protocols, hooks, and MCP registration."""
    print("\n🔧 에이전트 설정 수리 중...\n")
    agents = detect_agents()
    installed = [name for name, detected in agents.items() if detected]
    selected = args.agents if args.agents else installed
    selected = [s for s in selected if s in installed]
    if not selected:
        print(red("  수리할 설치된 에이전트가 없습니다."))
        return 1

    repair_skills = bool(getattr(args, "repair_skills", False))
    scope = "user"
    ok_count = 0
    for name in selected:
        adapter_cls = ADAPTER_REGISTRY[name]
        adapter = adapter_cls()  # type: ignore[abstract]
        print(f"⚙️  {adapter.display_name} 수리 중...")
        result = adapter.configure(scope=scope, repair=True, repair_skills=repair_skills)
        if result.get("success"):
            print("   ✓ 수리 완료")
            ok_count += 1
        else:
            print(yellow("   ! 일부 단계 실패 — setup --check 로 확인하세요"))
    print(
        f"\n{green(f'✅ {ok_count}/{len(selected)} 에이전트 수리 완료.')} 에이전트를 재시작하세요."
    )
    return 0 if ok_count == len(selected) else 1


def cmd_sync(args: argparse.Namespace) -> int:
    """Re-apply global agent configuration (same as setup for each adapter)."""
    from pathlib import Path

    from ..harness.spec import HarnessSpec

    print("\n🔄 Harness / 에이전트 전역 동기화 중...\n")

    harness_path = Path.cwd() / ".maru" / "harness.yaml"
    if harness_path.is_file():
        print(f"   ℹ 하네스 파일 사용: {harness_path.resolve()}")
    else:
        print(
            yellow(
                f"   ⚠ `.maru/harness.yaml` 없음 — 기본 스펙으로 전역 에이전트만 재설정합니다. "
                f"(프로젝트 데이터는 `{Path.cwd() / '.maru'}` / `maru-deep-pro-search init`)"
            )
        )

    # Validates YAML parses; spec fields are not yet merged into every adapter.
    HarnessSpec.from_project()

    scope = "user"
    ok_count = 0
    fail_count = 0

    for _name, adapter_cls in ADAPTER_REGISTRY.items():
        adapter = adapter_cls()  # type: ignore[abstract]
        if not adapter.detect():
            continue
        try:
            result = adapter.configure(scope=scope)
            if result.get("success"):
                print(f"   ✓ {adapter.display_name} 동기화 완료")
                ok_count += 1
            else:
                print(f"   ⚠ {adapter.display_name} 동기화 실패 또는 변경 없음")
                fail_count += 1
        except Exception as exc:
            print(f"   ✗ {adapter.display_name} 실패: {exc}")
            fail_count += 1

    print()
    if fail_count:
        print(red(f"총 {fail_count}개 에이전트 동기화 실패."))
    if ok_count:
        print(green(f"총 {ok_count}개 에이전트 동기화 완료."))
    return 1 if fail_count else 0


def main(argv: list[str] | None = None) -> int:
    from pathlib import Path

    prog = Path(sys.argv[0]).name if sys.argv else "maru-deep-pro-search"
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Setup tool for maru-deep-pro-search — installs MCP config and "
            "injects research-first rules into 20 supported AI agents."
        ),
        epilog=(
            "Examples:\n"
            "  maru-deep-pro-search setup              # Auto-detect and configure all agents\n"
            "  maru-deep-pro-search setup --agents cursor claude  # Configure specific agents\n"
            "  maru-deep-pro-search setup --list       # Show detected agents\n"
            "  maru-deep-pro-search setup --check      # Verify config status\n"
            "  maru-deep-pro-search setup --repair     # Fix stale hooks / duplicate protocol\n"
            "  maru-deep-pro-search setup --check --agents cursor  # Check specific agents\n"
            "  maru-deep-pro-search setup --restore    # Restore from backup\n"
            "\nSupported agents: " + ", ".join(sorted(ADAPTER_REGISTRY.keys()))
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup command (default)
    setup_parser = subparsers.add_parser(
        "setup",
        help="Configure AI agents with MCP settings and research-first rules",
        description="Auto-detect installed AI agents and inject MCP configuration.",
    )
    setup_parser.add_argument(
        "--agents",
        nargs="+",
        choices=list(ADAPTER_REGISTRY.keys()),
        metavar="AGENT",
        help="Specific agents to configure (default: auto-detect all)",
    )
    setup_parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore agent configs from previous backups",
    )
    setup_parser.add_argument(
        "--list",
        action="store_true",
        help="List all detected AI agents and their status",
    )
    setup_parser.add_argument(
        "--check",
        action="store_true",
        help="Check if MCP configs are correctly installed",
    )
    setup_parser.add_argument(
        "--repair",
        action="store_true",
        help="Repair configs (refresh protocol, hooks, MCP; skips skills unless --repair-skills)",
    )
    setup_parser.add_argument(
        "--repair-skills",
        action="store_true",
        help="With --repair, also overwrite packaged SKILL.md files",
    )

    # sync command
    subparsers.add_parser(
        "sync",
        help="Re-apply global agent configs (warns if .maru/harness.yaml is missing)",
        description=(
            "Re-runs the same global `configure()` as setup for all detected agents. "
            "If `.maru/harness.yaml` exists in the current directory it is validated/loaded "
            "for future harness-driven customization; adapters today use packaged protocol text."
        ),
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
        if args.repair:
            return cmd_repair(args)
        return cmd_setup(args)

    if args.command == "sync":
        return cmd_sync(args)

    # Default: run setup if no subcommand given
    return cmd_setup(args)


if __name__ == "__main__":
    sys.exit(main())
