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
        description="Check for updates and optionally upgrade maru-deep-pro-search.",
        epilog="Examples:\n"
        "  maru-deep-pro-search update --check   # Only check\n"
        "  maru-deep-pro-search update           # Check and install\n"
        "  maru-deep-pro-search update --dry-run # Show install plan only",
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

    print(f"\n{bold('📦 maru-deep-pro-search Update')}\n")

    result = check_for_update()

    if result.error:
        print(f"{red('❌')} {result.error}")
        return 1

    print(f"  Installed: {cyan(result.current_version)}")
    print(f"  PyPI latest: {cyan(result.latest_version or 'unknown')}")

    if not result.update_available:
        print(f"\n{green('✅')} You are on the latest version.")
        return 0

    notice = get_update_notice(result)
    if notice:
        print(notice)

    if args.check:
        return 0

    print(f"{yellow('⬆️  Updating...')}\n")
    with_setup = auto_setup_enabled(args.with_setup)
    success, msg = perform_update(dry_run=args.dry_run, with_setup=with_setup)
    print(msg)
    if success and with_setup and not args.dry_run:
        from .setup import run_repair_after_update

        print(f"\n{bold('⚙️  Refreshing agent configs...')}\n")
        repair_code = run_repair_after_update()
        if repair_code != 0:
            print(yellow(f"   Agent repair had issues. Try: {SETUP_REPAIR_HINT}"))
            return repair_code
        print(green("   ✓ Agent configs repaired for detected agents."))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
