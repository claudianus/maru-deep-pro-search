"""Plugin management CLI — `maru-deep-pro-search plugin`."""

from __future__ import annotations

import argparse
import sys

from ..harness.plugin import PluginManager


def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"


def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m"


def cmd_list(args: argparse.Namespace) -> int:
    mgr = PluginManager(args.path)
    plugins = mgr.list_plugins()
    if not plugins:
        print(_yellow("설치된 플러그인이 없습니다."))
        print("  설치: maru-deep-pro-search plugin install <git-url-or-path>")
        return 0

    print(f"\n📦 설치된 플러그인 ({len(plugins)}개)\n")
    for p in plugins:
        agents = ", ".join(p.agents) if p.agents else "all"
        print(f"  {_green('●')} {p.name}  v{p.version}")
        print(f"     {p.description or '(설명 없음)'}")
        print(f"     대상 에이전트: {agents}")
        print(f"     명령어: {len(p.commands)}개  규칙: {len(p.rules)}개  훅: {len(p.hooks)}개")
        print()
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    mgr = PluginManager(args.path)
    try:
        plugin = mgr.install(args.source)
        print(_green(f"✓ {plugin.name} v{plugin.version} 설치 완료"))
        if plugin.commands:
            print(f"  추가된 명령어: {', '.join(c.name for c in plugin.commands)}")
        if plugin.hooks:
            print(f"  추가된 훅: {', '.join(h.event for h in plugin.hooks)}")
        print(_yellow("  maru-deep-pro-search setup를 다시 실행해 에이전트에 적용하세요."))
        return 0
    except Exception as exc:
        print(_red(f"✗ 설치 실패: {exc}"))
        return 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    mgr = PluginManager(args.path)
    if mgr.uninstall(args.name):
        print(_green(f"✓ {args.name} 제거 완료"))
        return 0
    print(_red(f"✗ {args.name}를 찾을 수 없습니다."))
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search-plugin",
        description="Manage maru harness plugins.",
        epilog="Examples:\n  maru-deep-pro-search-plugin list\n  maru-deep-pro-search-plugin install https://github.com/user/plugin.git\n  maru-deep-pro-search-plugin uninstall my-plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--path", default=".", help="Project root (default: .)")
    subparsers = parser.add_subparsers(dest="command", help="Plugin commands")

    subparsers.add_parser("list", help="List installed plugins")

    install_parser = subparsers.add_parser("install", help="Install a plugin from Git URL or local path")
    install_parser.add_argument("source", help="Git URL or local path to plugin")

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove an installed plugin")
    uninstall_parser.add_argument("name", help="Plugin name to remove")

    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    if args.command == "install":
        return cmd_install(args)
    if args.command == "uninstall":
        return cmd_uninstall(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
