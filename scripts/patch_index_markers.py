#!/usr/bin/env python3
"""Insert <!--@panel:ID@--> markers into docs/index.html (replace PNG img blocks)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"


def main() -> int:
    t = INDEX.read_text(encoding="utf-8")
    if "assets/marketing/panels.css" not in t:
        t = t.replace(
            '<link rel="stylesheet" href="maru-tailwind.css">',
            '<link rel="stylesheet" href="maru-tailwind.css">\n'
            '<link rel="stylesheet" href="assets/marketing/panels.css">\n'
            '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">',
            1,
        )
    if ".mcp-demo-host" not in t:
        t = t.replace(
            ".shot-frame img { display: block; width: 100%; height: auto; }",
            ".shot-frame img { display: block; width: 100%; height: auto; }\n"
            ".shot-frame.mcp-demo-host { padding: 0; }\n"
            ".shot-frame.mcp-demo-host .mcp-demo { width: 100%; }",
            1,
        )

    t, _ = re.subn(
        r"(<div class=\"mt-12 max-w-5xl mx-auto scroll-reveal\">\s*)"
        r"<div class=\"shot-frame\">\s*"
        r"<img src=\"assets/screenshots/tech_compare@2x\.png\"[^>]*/>\s*",
        r'\1<div class="shot-frame mcp-demo-host"><!--@panel:tech_compare@-->',
        t,
        count=1,
    )
    t, _ = re.subn(
        r"(<div class=\"mt-12 max-w-5xl mx-auto scroll-reveal\">\s*)"
        r"<div class=\"shot-frame\">\s*"
        r"<img src=\"assets/screenshots/tech_compare@2x\.png\"[^>]*/>\s*",
        r'\1<div class="shot-frame mcp-demo-host"><!--@panel:tech_compare@-->',
        t,
        count=1,
    )

    for old, new in (
        (
            '<div class="shot-frame mb-3"><img src="assets/screenshots/tech_compare@2x.png" width="1280" height="720" loading="lazy" alt="Research Trace"/></div>',
            '<div class="shot-frame mcp-demo-host mb-3"><!--@panel:tech_compare@--></div>',
        ),
        (
            '<div class="shot-frame mb-3"><img src="assets/screenshots/tech_compare@2x.png" width="1280" height="720" loading="lazy" alt="Research Trace"/></div>',
            '<div class="shot-frame mcp-demo-host mb-3"><!--@panel:tech_compare@--></div>',
        ),
        (
            '<div class="shot-frame mb-3"><img src="assets/screenshots/korean_market@2x.png" width="1280" height="720" loading="lazy" alt="answer tool"/></div>',
            '<div class="shot-frame mcp-demo-host mb-3"><!--@panel:korean_market@--></div>',
        ),
        (
            '<div class="shot-frame mb-3"><img src="assets/screenshots/quality_signals@2x.png" width="1280" height="640" loading="lazy" alt="Source scores"/></div>',
            '<div class="shot-frame mcp-demo-host mb-3"><!--@panel:quality_signals@--></div>',
        ),
        (
            '<div class="shot-frame mb-3"><img src="assets/screenshots/embedding@2x.png" width="1280" height="720" loading="lazy" alt="Granite embedding"/></div>',
            '<div class="shot-frame mcp-demo-host mb-3"><!--@panel:embedding@--></div>',
        ),
        (
            '<div class="shot-frame mb-3"><img src="assets/screenshots/embedding@2x.png" width="1280" height="720" loading="lazy" alt="Granite embedding"/></div>',
            '<div class="shot-frame mcp-demo-host mb-3"><!--@panel:embedding@--></div>',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/setup_flow@2x.png" width="960" height="520" loading="lazy" alt="warmup CLI"/><div class="shot-caption">warmup-embeddings</div></div>',
            '<div class="shot-frame mcp-demo-host"><!--@panel:setup_flow@--><div class="shot-caption">warmup-embeddings</div></div>',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/setup_flow@2x.png" width="960" height="520" loading="lazy" alt="warmup CLI"/><div class="shot-caption">warmup-embeddings</div></div>',
            '<div class="shot-frame mcp-demo-host"><!--@panel:setup_flow@--><div class="shot-caption">warmup-embeddings</div></div>',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/compare_split@2x.png" width="1100" height="620" loading="lazy" alt="compare"/><div class="shot-caption">P@5 +86% · 9 engines · $0</div></div>',
            '<div class="shot-frame mcp-demo-host"><!--@panel:compare_split@--><div class="shot-caption">P@5 +86% · 9 engines · $0</div></div>',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/compare_split@2x.png" width="1100" height="620" loading="lazy" alt="Built-in vs maru benchmark"/><div class="shot-caption ko">',
            '<div class="shot-frame mcp-demo-host"><!--@panel:compare_split@--><div class="shot-caption ko">',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/compare_split@2x.png" width="1100" height="620" loading="lazy" alt="Built-in vs maru benchmark"/><div class="shot-caption ko">',
            '<div class="shot-frame mcp-demo-host"><!--@panel:compare_split@--><div class="shot-caption ko">',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/quality_signals@2x.png" width="1280" height="640" loading="lazy" alt="Source quality metadata"/><div class="shot-caption ko">',
            '<div class="shot-frame mcp-demo-host"><!--@panel:quality_signals@--><div class="shot-caption ko">',
        ),
        (
            '<div class="shot-frame mt-3 max-w-xl"><img src="assets/screenshots/embedding@2x.png" width="960" height="540" loading="lazy" alt="Granite embedding research output"/></div>',
            '<div class="shot-frame mcp-demo-host mt-3 max-w-xl"><!--@panel:embedding@--></div>',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/korean_market@2x.png" width="1280" height="720" loading="lazy" alt="answer MCP packet"/><div class="shot-caption">answer · 갤럭시 S24 중고 시세</div></div>',
            '<div class="shot-frame mcp-demo-host"><!--@panel:korean_market@--><div class="shot-caption">answer · 갤럭시 S24 중고 시세</div></div>',
        ),
        (
            '<div class="shot-frame"><img src="assets/screenshots/korean_market@2x.png" width="1280" height="720" loading="lazy" alt="answer MCP packet"/><div class="shot-caption">answer · 갤럭시 S24 중고 시세</div></div>',
            '<div class="shot-frame mcp-demo-host"><!--@panel:korean_market@--><div class="shot-caption">answer · 갤럭시 S24 중고 시세</div></div>',
        ),
    ):
        t = t.replace(old, new)

    t = re.sub(
        r'<div class="shot-frame mb-8 scroll-reveal">\s*<div class="shot-frame mb-8 scroll-reveal">\s*'
        r'<img src="assets/screenshots/setup_flow@2x\.png"[^>]*/>\s*',
        '<div class="shot-frame mcp-demo-host mb-8 scroll-reveal"><!--@panel:setup_flow@-->',
        t,
        count=1,
    )
    t = re.sub(
        r'<div class="shot-frame mb-8 scroll-reveal">\s*'
        r'<img src="assets/screenshots/setup_flow@2x\.png"[^>]*/>\s*',
        '<div class="shot-frame mcp-demo-host mb-8 scroll-reveal"><!--@panel:setup_flow@-->',
        t,
        count=1,
    )

    t = t.replace(
        "Playwright로 렌더했습니다.",
        "fixture 기반 라이브 HTML 패널로 렌더했습니다.",
    )
    t = t.replace(
        "Screenshots from live tool runs + Playwright templates.",
        "Live HTML panels from fixtures (selectable text). OG image only uses Playwright.",
    )

    INDEX.write_text(t, encoding="utf-8")
    print(f"Markers: {len(re.findall(r'<!--@panel:', t))}")
    print(f"Non-og imgs: {len(re.findall(r'assets/screenshots/(?!og-card)', t))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
