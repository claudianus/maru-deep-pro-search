#!/usr/bin/env python3
"""Embed live HTML MCP demo panels into GitHub Pages (PNG only for og:image).

Usage:
    uv run python scripts/embed_marketing_panels.py
    uv run python scripts/embed_marketing_panels.py --fetch   # data-panel + fetch partials
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIALS_DIR = (ROOT / "docs" / "partials" / "panels").resolve()
CSS_OUT = (ROOT / "docs" / "assets" / "marketing" / "panels.css").resolve()
INDEX_HTML = (ROOT / "docs" / "index.html").resolve()

sys.path.insert(0, str(ROOT / "scripts"))
from marketing_panels import build_all_panels, scoped_panels_css  # noqa: E402


def write_panels() -> dict[str, str]:
    panels = build_all_panels()
    PARTIALS_DIR.mkdir(parents=True, exist_ok=True)
    for panel_id, html_fragment in panels.items():
        path = PARTIALS_DIR / f"{panel_id}.html"
        path.write_text(html_fragment + "\n", encoding="utf-8")
        print(f"Wrote {path}")
    CSS_OUT.parent.mkdir(parents=True, exist_ok=True)
    CSS_OUT.write_text(scoped_panels_css(), encoding="utf-8")
    print(f"Wrote {CSS_OUT}")
    return panels


def patch_index_html(panels: dict[str, str], *, use_fetch: bool) -> None:
    text = INDEX_HTML.read_text(encoding="utf-8")
    missing: list[str] = []
    for panel_id, fragment in panels.items():
        marker = f"<!--@panel:{panel_id}@-->"
        if marker not in text:
            missing.append(panel_id)
            continue
        if use_fetch:
            replacement = f'<div class="mcp-demo" data-panel="{panel_id}" aria-busy="true"></div>'
        else:
            replacement = fragment
        text = text.replace(marker, replacement)
    if missing:
        print(f"Warning: markers missing: {', '.join(missing)}")
    INDEX_HTML.write_text(text, encoding="utf-8")
    print(f"Updated {INDEX_HTML} ({'fetch' if use_fetch else 'inline'})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed marketing MCP panels for GitHub Pages")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Keep empty data-panel shells (load partials via JS). Default: inline HTML.",
    )
    args = parser.parse_args()
    panels = write_panels()
    patch_index_html(panels, use_fetch=args.fetch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
