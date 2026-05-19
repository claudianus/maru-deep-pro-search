#!/usr/bin/env python3
"""Render og:image PNG only (live panels are embedded via embed_marketing_panels.py).

Usage:
    uv pip install playwright
    playwright install chromium
    uv run python scripts/render_marketing_screenshots.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "assets" / "screenshots"

sys.path.insert(0, str(ROOT / "scripts"))
from marketing_panels import build_og_card_html  # noqa: E402


def render_og_card() -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Install playwright: uv pip install playwright && playwright install chromium"
        ) from exc

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_doc = build_og_card_html()
    out = OUT_DIR / "og-card@2x.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1200, "height": 630},
            device_scale_factor=2,
        )
        page.set_content(html_doc, wait_until="networkidle")
        page.screenshot(path=str(out), type="png")
        page.close()
        browser.close()
    print(f"Wrote {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    render_og_card()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
