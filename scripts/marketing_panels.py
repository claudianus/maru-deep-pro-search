"""Shared fixture → HTML panel builders for marketing (Pages + OG screenshot)."""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "docs" / "fixtures" / "raw"
SYN_DIR = ROOT / "docs" / "fixtures" / "synthesis"
TPL_DIR = ROOT / "docs" / "screenshots" / "templates"
BASE_CSS_PATH = TPL_DIR / "_base.css"


def md_to_panel(text: str, max_lines: int = 48) -> str:
    """Minimal markdown → HTML for demo panels."""
    lines = text.splitlines()
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
            out.append("<div class='meta'>… more in live MCP output</div>")
            break
    return "\n".join(out)


def read_fixture(fid: str) -> tuple[str, str]:
    raw = (RAW_DIR / f"{fid}.md").read_text(encoding="utf-8")
    syn_path = SYN_DIR / f"{fid}.md"
    syn = syn_path.read_text(encoding="utf-8") if syn_path.exists() else ""
    return raw, syn


def inject(template: str, **slots: str) -> str:
    for key, val in slots.items():
        template = template.replace(f"{{{{{key}}}}}", val)
    leftover = re.findall(r"\{\{(\w+)\}\}", template)
    if leftover:
        msg = ", ".join(sorted(set(leftover)))
        raise ValueError(f"Unfilled template placeholders: {msg}")
    return template


def load_template(name: str) -> str:
    return (TPL_DIR / name).read_text(encoding="utf-8").replace("{{BASE_CSS}}", "")


def body_inner(full_html: str) -> str:
    match = re.search(r"<body[^>]*>(.*)</body>", full_html, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else full_html


def extract_source_chips(raw: str) -> str:
    chips: list[str] = []
    for m in re.finditer(r"#### \[(\d+)\] ([^\n]+)", raw):
        chips.append(f'<span class="chip">[{m.group(1)}] {html.escape(m.group(2)[:42])}</span>')
        if len(chips) >= 6:
            break
    return "".join(chips) if chips else '<span class="chip">[1] Source</span>'


def sources_table(raw: str) -> str:
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
            f"<td class='mono'>{html.escape(access.group(1).strip()) if access else '—'}</td>"
            f"<td class='mono'>{html.escape(noise.group(1)) if noise else '—'}</td>"
            "</tr>"
        )
        if len(rows) >= 8:
            break
        i += 2
    if not rows:
        rows.append("<tr><td colspan='6'>No sources parsed</td></tr>")
    return "\n".join(rows)


def md_to_terminal(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("```"):
            continue
        if line.strip():
            lines.append(html.escape(line))
    return "<br/>".join(lines[-18:])


def wrap_panel(panel_id: str, inner: str) -> str:
    return (
        f'<div class="mcp-demo" data-panel="{html.escape(panel_id)}" '
        f'role="img" aria-label="{html.escape(panel_id)} demo">\n{inner}\n</div>'
    )


def build_cursor_tool(
    panel_id: str,
    *,
    tool_name: str,
    chat: str,
    raw_fixture: str,
    max_lines: int = 42,
) -> str:
    inner = body_inner(
        inject(
            load_template("cursor-mcp-tool.html"),
            tool_name=tool_name,
            panel_body=md_to_panel(raw_fixture, max_lines),
        )
    )
    inner = inner.replace(
        "Compare FastAPI vs Django for our 2026 API rewrite.",
        html.escape(chat),
    )
    return wrap_panel(panel_id, inner)


def build_cursor_answer(panel_id: str, *, query: str, raw: str, syn: str) -> str:
    inner = body_inner(
        inject(
            load_template("cursor-answer.html"),
            query=html.escape(query),
            panel_body=md_to_panel(syn or raw, 28),
            sources_row=extract_source_chips(raw),
        )
    )
    return wrap_panel(panel_id, inner)


def build_quality_signals(panel_id: str, raw: str) -> str:
    inner = body_inner(
        inject(
            load_template("quality-signals.html"),
            sources_table=sources_table(raw),
        )
    )
    return wrap_panel(panel_id, inner)


def build_terminal(panel_id: str, raw: str) -> str:
    inner = body_inner(
        inject(
            load_template("terminal-setup.html"),
            terminal_body=md_to_terminal(raw),
        )
    )
    return wrap_panel(panel_id, inner)


def build_compare_split(panel_id: str) -> str:
    inner = body_inner(load_template("compare-split.html"))
    return wrap_panel(panel_id, inner)


def build_all_panels() -> dict[str, str]:
    raw_tc, _ = read_fixture("tech_compare")
    raw_ko, syn_ko = read_fixture("korean_market")
    raw_sec, _ = read_fixture("security")
    raw_emb, _ = read_fixture("embedding")
    raw_setup, _ = read_fixture("setup_flow")

    return {
        "tech_compare": build_cursor_tool(
            "tech_compare",
            tool_name="deep_research",
            chat="Django vs FastAPI 2026 — when to choose?",
            raw_fixture=raw_tc,
        ),
        "korean_market": build_cursor_answer(
            "korean_market",
            query="갤럭시 S24 중고 시세 추천 2026",
            raw=raw_ko,
            syn=syn_ko,
        ),
        "quality_signals": build_quality_signals("quality_signals", raw_sec),
        "embedding": build_cursor_tool(
            "embedding",
            tool_name="deep_research",
            chat="Granite 97M vs e5-small on MTEB multilingual",
            raw_fixture=raw_emb,
            max_lines=36,
        ),
        "setup_flow": build_terminal("setup_flow", raw_setup),
        "compare_split": build_compare_split("compare_split"),
    }


def scoped_panels_css() -> str:
    """Scope screenshot template CSS under .mcp-demo for GitHub Pages."""
    base = BASE_CSS_PATH.read_text(encoding="utf-8")
    lines: list[str] = [
        "/* Auto-generated — run scripts/embed_marketing_panels.py */",
        ".mcp-demo {",
        "  font-family: 'JetBrains Mono', ui-monospace, monospace;",
        "  font-size: 11px;",
        "  line-height: 1.45;",
        "  color: #e6edf3;",
        "  background: #0d1117;",
        "}",
        ".mcp-demo .layout { min-height: 0; height: auto; max-height: 420px; }",
        ".mcp-demo .tool-body { max-height: 300px; overflow-y: auto; }",
        ".mcp-demo .sidebar { width: 140px; }",
        "@media (max-width: 640px) { .mcp-demo .sidebar { display: none; } }",
    ]
    for rule in base.split("}"):
        chunk = rule.strip()
        if not chunk:
            continue
        if chunk.startswith("*"):
            _, _, decl = chunk.partition("{")
            lines.append(f".mcp-demo {{{decl}}}")
            continue
        if "{" not in chunk:
            continue
        sel, _, decl = chunk.partition("{")
        sel = sel.strip()
        if not sel or sel == "body":
            continue
        scoped_sel = ", ".join(f".mcp-demo {s.strip()}" for s in sel.split(",") if s.strip())
        lines.append(f"{scoped_sel} {{{decl}}}")
    return "\n".join(lines) + "\n"


def build_og_card_html() -> str:
    raw_tc, _ = read_fixture("tech_compare")
    tpl = (
        (TPL_DIR / "og-card.html")
        .read_text(encoding="utf-8")
        .replace(
            "{{BASE_CSS}}",
            BASE_CSS_PATH.read_text(encoding="utf-8"),
        )
    )
    return inject(tpl, panel_snippet=md_to_panel(raw_tc, 14))
