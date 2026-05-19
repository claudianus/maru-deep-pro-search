#!/usr/bin/env python3
"""Embed live HTML MCP demo panels into GitHub Pages (PNG only for og:image).

Usage:
    uv run python scripts/embed_marketing_panels.py
    uv run python scripts/embed_marketing_panels.py --fetch   # data-panel + fetch partials
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIALS_DIR = (ROOT / "docs" / "partials" / "panels").resolve()
CSS_OUT = (ROOT / "docs" / "assets" / "marketing" / "panels.css").resolve()
INDEX_HTML = (ROOT / "docs" / "index.html").resolve()

_DIV_TAG = re.compile(r"<(/?)div\b", re.IGNORECASE)


def _mcp_demo_open(panel_id: str) -> str:
    return '<div class="mcp-demo" data-panel="' + panel_id + '"'


def _mcp_demo_span(html: str, panel_id: str, search_from: int = 0) -> tuple[int, int] | None:
    """Return [start, end) of the next mcp-demo block for panel_id."""
    start = html.find(_mcp_demo_open(panel_id), search_from)
    if start < 0:
        return None
    depth = 0
    for m in _DIV_TAG.finditer(html, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            end = html.find(">", m.end()) + 1
            return start, end
    return None


def _replace_one_mcp_demo(html: str, panel_id: str, replacement: str) -> tuple[str, bool]:
    """Replace the next mcp-demo block that differs from replacement."""
    search_from = 0
    while True:
        span = _mcp_demo_span(html, panel_id, search_from)
        if span is None:
            return html, False
        start, end = span
        if html[start:end] != replacement:
            return html[:start] + replacement + html[end:], True
        search_from = end


def _upsert_panel(html: str, panel_id: str, replacement: str) -> tuple[str, int]:
    """Insert or refresh panel HTML; returns (html, count_replaced)."""
    marker = f"<!--@panel:{panel_id}@-->"
    count = 0
    while marker in html:
        html = html.replace(marker, replacement, 1)
        count += 1
    while True:
        html, ok = _replace_one_mcp_demo(html, panel_id, replacement)
        if not ok:
            break
        count += 1
    return html, count


def write_panels() -> dict[str, str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from marketing_panels import build_all_panels, scoped_panels_css  # noqa: E402

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
    total = 0
    for panel_id, fragment in panels.items():
        if use_fetch:
            replacement = (
                "<"
                + "div"
                + ' class="mcp-demo" data-panel="'
                + panel_id
                + '" aria-busy="true"></div>'
            )
        else:
            replacement = fragment
        text, n = _upsert_panel(text, panel_id, replacement)
        total += n
        if n == 0 and _mcp_demo_open(panel_id) not in text:
            missing.append(panel_id)
    if missing:
        print(f"Warning: no slots for: {', '.join(missing)}")
    INDEX_HTML.write_text(text, encoding="utf-8")
    print(f"Updated {INDEX_HTML} ({total} slot(s), {'fetch' if use_fetch else 'inline'})")


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
