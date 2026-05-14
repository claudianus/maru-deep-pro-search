"""KnowledgeStore statistics CLI — inspect research cache health."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..harness.persistence import KnowledgeStore
from .env_check import bold, cyan, green, yellow


def cmd_stats(args: argparse.Namespace) -> int:
    """Display KnowledgeStore statistics."""
    db_path = args.db or KnowledgeStore._default_db_path()
    store = KnowledgeStore(db_path)

    try:
        stats = store.get_stats()
    except Exception as exc:
        print(f"Error reading knowledge store: {exc}")
        return 1

    print(f"\n{bold('📊 Knowledge Store Stats')}")
    print(f"  Database: {db_path}")
    print(f"  Total entries: {green(str(stats.get('total_entries', 0)))}")
    print(f"  Recent (7d): {cyan(str(stats.get('last_7_days', 0)))}")

    top = stats.get("top_queries", [])
    if top:
        print(f"\n{bold('🔥 Top Queries')}:")
        for item in top:
            if isinstance(item, dict):
                query = item["query"]
                count = item["access_count"]
            else:
                query, count = item
            print(f"  {count:3d}x  {query[:60]}")

    # Domain stats
    try:
        conn = store._connect()
        domains = conn.execute(
            "SELECT domain, avg_duration_ms, success_count, failure_count FROM domain_stats ORDER BY success_count DESC LIMIT 10"
        ).fetchall()
        if domains:
            print(f"\n{bold('🌐 Domain Performance')}:")
            for row in domains:
                rate = (
                    row["success_count"] / max(row["success_count"] + row["failure_count"], 1) * 100
                )
                color = green if rate > 80 else yellow if rate > 50 else "\033[91m"
                print(
                    f"  {color}{rate:5.1f}%\033[0m  {row['domain'][:40]:40s}  avg={row['avg_duration_ms']:.0f}ms"
                )
    except Exception:
        pass

    # Size on disk
    try:
        size = Path(db_path).stat().st_size
        size_mb = size / (1024 * 1024)
        print(f"\n  Size on disk: {size_mb:.2f} MB")
    except Exception:
        pass

    return 0


def main(argv: list[str] | None = None) -> int:
    """Display KnowledgeStore statistics and health."""
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search stats",
        description="Display KnowledgeStore statistics, cache health, and usage metrics.",
        epilog="Example: maru-deep-pro-search stats --db ./.maru/knowledge.db",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to knowledge database (default: ./.maru/knowledge.db)",
    )
    args = parser.parse_args(argv)
    return cmd_stats(args)
