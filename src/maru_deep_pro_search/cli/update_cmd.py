"""`maru-deep-pro-search update` — Self-update command."""

from __future__ import annotations

import argparse
import sys

from ..utils.updater import (
    SETUP_REPAIR_HINT,
    auto_setup_enabled,
    check_for_update,
    get_update_notice,
    perform_update,
)
from .env_check import bold, cyan, green, red, yellow


def main(argv: list[str] | None = None) -> int:
    """Check for and optionally apply updates."""
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search update",
        description="PyPI에서 새 버전을 확인하고 설치합니다.",
        epilog=(
            "예시:\n"
            "  maru-deep-pro-search update --check        # 확인만\n"
            "  maru-deep-pro-search update                # 설치\n"
            "  maru-deep-pro-search update --with-setup   # 설치 후 setup --repair\n"
            "  maru-deep-pro-search update --dry-run      # 설치 계획만 표시"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if an update is available, do not install.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without installing.",
    )
    parser.add_argument(
        "--with-setup",
        action="store_true",
        help="After upgrade, run setup --repair on detected agents (same as MARU_UPDATE_AUTO_SETUP=1).",
    )

    args = parser.parse_args(argv)

    print(f"\n{bold('📦 maru-deep-pro-search 업데이트')}\n")

    result = check_for_update()

    if result.error:
        print(f"{red('❌')} {result.error}")
        return 1

    print(f"  설치됨: {cyan(result.current_version)}")
    print(f"  PyPI 최신: {cyan(result.latest_version or 'unknown')}")

    if not result.update_available:
        print(f"\n{green('✅')} 최신 버전입니다.")
        return 0

    notice = get_update_notice(result)
    if notice:
        print(notice)

    if args.check:
        return 0

    print(f"{yellow('⬆️  업데이트 중...')}\n")
    with_setup = auto_setup_enabled(args.with_setup)
    success, msg = perform_update(dry_run=args.dry_run, with_setup=with_setup)
    print(msg)
    if success and with_setup and not args.dry_run:
        from .setup import run_repair_after_update

        print(f"\n{bold('⚙️  에이전트 설정 갱신 중...')}\n")
        repair_code = run_repair_after_update()
        if repair_code != 0:
            print(yellow(f"   일부 에이전트 수리 실패. {SETUP_REPAIR_HINT}"))
            return repair_code
        print(green("   ✓ 감지된 에이전트 설정을 수리했습니다."))
    if success and not args.dry_run:
        print(
            f"\n{yellow('💡')} Cursor·Claude Code 등 **에이전트를 재시작**한 뒤 "
            f"`maru-deep-pro-search setup --check`로 확인하세요."
        )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
