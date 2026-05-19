#!/usr/bin/env python3
"""Render marketing screenshots from fixtures + HTML templates (Playwright).

Usage:
    uv pip install playwright
    playwright install chromium
    uv run python scripts/render_marketing_screenshots.py
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "docs" / "fixtures" / "raw"
SYN_DIR = ROOT / "docs" / "fixtures" / "synthesis"
TPL_DIR = ROOT / "docs" / "screenshots" / "templates"
OUT_DIR = ROOT / "docs" / "assets" / "screenshots"


def _md_to_panel(text: str, max_lines: int = 48) -> str:
    """Minimal markdown → HTML for screenshot panels."""
    lines = text.splitlines()
    # Strip external content wrapper for display
    out: list[str] = []
    skip_prefixes = ("[EXTERNAL", "[END EXTERNAL", "_research_id", "_receipt", "_query:")
    for line in lines:
        if any(line.startswith(p) for p in skip_prefixes):
            continue
        if line.startswith("## "):
            out.append(f'<div class="h2">{html.escape(line[3:])}</div>')
        elif line.startswith("### "):
            out.append(f'<div class="h3">{html.escape(line[4:])}</div>')
        elif line.startswith("#### "):
            out.append(f'<div class="h4">{html.escape(line[5:])}</div>')
        elif line.startswith("- "):
            out.append(f'<div class="li">{html.escape(line[2:])}</div>')
        elif line.startswith("_") and line.endswith("_"):
            out.append(f'<div class="meta">{html.escape(line.strip("_"))}</div>')
        elif line.strip() == "":
            out.append("<div class='sp'></div>")
        else:
            line_esc = html.escape(line)
            line_esc = re.sub(r"\[(\d+)\]", r'<span class="cite">[\1]</span>', line_esc)
            line_esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line_esc)
            out.append(f"<div class='p'>{line_esc}</div>")
        if len(out) >= max_lines:
            out.append("<div class='meta'>… truncated for screenshot</div>")
            break
    return "\n".join(out)


def _read_fixture(fid: str) -> tuple[str, str]:
    raw = (RAW_DIR / f"{fid}.md").read_text(encoding="utf-8")
    syn_path = SYN_DIR / f"{fid}.md"
    syn = syn_path.read_text(encoding="utf-8") if syn_path.exists() else ""
    return raw, syn


def _inject(template: str, **slots: str) -> str:
    for key, val in slots.items():
        template = template.replace(f"{{{{{key}}}}}", val)
    return template


def _load_template(name: str) -> str:
    base_css = (TPL_DIR / "_base.css").read_text(encoding="utf-8")
    html_doc = (TPL_DIR / name).read_text(encoding="utf-8")
    return html_doc.replace("{{BASE_CSS}}", base_css)


def render_all() -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Install playwright: uv pip install playwright && playwright install chromium"
        ) from exc

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[str, str, int, int]] = []

    raw_tc, _ = _read_fixture("tech_compare")
    jobs.append(
        (
            "tech_compare",
            _inject(
                _load_template("cursor-mcp-tool.html"),
                tool_name="deep_research",
                query="FastAPI vs Django 2026 architecture comparison",
                panel_body=_md_to_panel(raw_tc, 42),
            ),
            1280,
            720,
        )
    )

    raw_ko, syn_ko = _read_fixture("korean_market")
    jobs.append(
        (
            "korean_market",
            _inject(
                _load_template("cursor-answer.html"),
                query="갤럭시 S24 중고 시세 추천 2026",
                panel_body=_md_to_panel(syn_ko or raw_ko, 28),
                sources_row=_extract_source_chips(raw_ko),
            ),
            1280,
            720,
        )
    )

    raw_sec, _ = _read_fixture("security")
    jobs.append(
        (
            "quality_signals",
            _inject(
                _load_template("quality-signals.html"),
                sources_table=_sources_table(raw_sec),
            ),
            1280,
            640,
        )
    )

    raw_emb, _ = _read_fixture("embedding")
    jobs.append(
        (
            "embedding",
            _inject(
                _load_template("cursor-mcp-tool.html"),
                tool_name="deep_research",
                query="Granite 97M vs multilingual-e5-small (MTEB)",
                panel_body=_md_to_panel(raw_emb, 40),
            ),
            1280,
            720,
        )
    )

    raw_setup, _ = _read_fixture("setup_flow")
    jobs.append(
        (
            "setup_flow",
            _inject(
                _load_template("terminal-setup.html"),
                terminal_body=_md_to_terminal(raw_setup),
            ),
            960,
            520,
        )
    )

    jobs.append(
        (
            "compare_split",
            _load_template("compare-split.html"),
            1100,
            620,
        )
    )

    # OG card from hero template
    jobs.append(
        (
            "og-card",
            _inject(
                _load_template("og-card.html"),
                panel_snippet=_md_to_panel(raw_tc, 14),
            ),
            1200,
            630,
        )
    )

    written: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, html_doc, width, height in jobs:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=2,
            )
            page.set_content(html_doc, wait_until="networkidle")
            out = OUT_DIR / f"{name}@2x.png"
            page.screenshot(path=str(out), type="png")
            written.append(out)
            print(f"Wrote {out}")
            page.close()
        browser.close()
    return written


def _extract_source_chips(raw: str) -> str:
    chips: list[str] = []
    for m in re.finditer(r"#### \[(\d+)\] ([^\n]+)", raw):
        chips.append(
            f'<span class="chip">[{m.group(1)}] {html.escape(m.group(2)[:42])}</span>'
        )
        if len(chips) >= 6:
            break
    return "".join(chips) if chips else '<span class="chip">[1] Source</span>'


def _sources_table(raw: str) -> str:
    rows: list[str] = []
    blocks = re.split(r"#### \[(\d+)\] ", raw)
    i = 1
    while i < len(blocks) - 1:
        cid = blocks[i]
        rest = blocks[i + 1]
        title_line = rest.split("\n", 1)[0].strip()
        meta = ""
        for line in rest.splitlines():
            if line.startswith("_score:"):
                meta = line
                break
        score = re.search(r"_score:\s*([\d.]+)", meta or "")
        cov = re.search(r"coverage:\s*([\d.]+%?)", meta or "")
        access = re.search(r"access:\s*([^|]+)", meta or "")
        noise = re.search(r"noise:\s*([-\d.]+)", meta or "")
        rows.append(
            "<tr>"
            f"<td class='mono'>[{cid}]</td>"
            f"<td>{html.escape(title_line[:56])}</td>"
            f"<td class='mono'>{score.group(1) if score else '—'}</td>"
            f"<td class='mono'>{cov.group(1) if cov else '—'}</td>"
            f"<td class='mono'>{access.group(1).strip() if access else '—'}</td>"
            f"<td class='mono'>{noise.group(1) if noise else '—'}</td>"
            "</tr>"
        )
        if len(rows) >= 8:
            break
        i += 2
    if not rows:
        rows.append("<tr><td colspan='6'>No sources parsed</td></tr>")
    return "\n".join(rows)


def _md_to_terminal(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("```"):
            continue
        if line.strip():
            lines.append(html.escape(line))
    return "<br/>".join(lines[-18:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    render_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
