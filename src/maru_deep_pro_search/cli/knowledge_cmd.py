"""Export/import KnowledgeStore bundles for team sharing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..harness.persistence import KnowledgeStore
from .env_check import bold, green


def cmd_export(args: argparse.Namespace) -> int:
    store = KnowledgeStore(args.db)
    count = store.export_bundle(args.output, max_entries=args.limit)
    print(f"{green('✓')} Exported {count} entries → {Path(args.output).resolve()}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    store = KnowledgeStore(args.db)
    count = store.import_bundle(args.input)
    db = args.db or str(KnowledgeStore._default_db_path())
    print(f"{green('✓')} Imported {count} entries into {db}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search-knowledge",
        description="Export or import .maru/knowledge.db research cache (portable JSON).",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Knowledge DB path (default: ./.maru/knowledge.db)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="Write knowledge bundle JSON")
    exp.add_argument(
        "-o",
        "--output",
        default="maru-knowledge-export.json",
        help="Output JSON path",
    )
    exp.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Max entries to export (default: 500)",
    )

    imp = sub.add_parser("import", help="Merge knowledge bundle JSON into local DB")
    imp.add_argument("input", help="Input JSON from export")

    args = parser.parse_args(argv)
    print(f"\n{bold('📦 Maru Knowledge')}\n")
    if args.command == "export":
        return cmd_export(args)
    return cmd_import(args)


if __name__ == "__main__":
    sys.exit(main())
