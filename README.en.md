<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>Force coding agents to research before they code.</strong><br>
  Zero API keys · 9-engine RRF+BM25+Granite 97M · Research Trace · 21 agent adapters
</p>

<p align="center">
  <a href="./README.md">🇰🇷 한국어</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/validate.yml?style=flat-square&label=validate" alt="Validate"></a>
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-deep-pro-search/">🌐 Website</a> ·
  <a href="https://claudianus.github.io/maru-deep-pro-search/#prompts">💬 Copy-paste prompts</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## Introduction

`maru-deep-pro-search` is an **agent harness + deep-research superset MCP** for Cursor, Claude Code, and peers. It builds web research → Granite semantic re-ranking → `[1]` citation packets, then enforces **research-before-code** via rules, session gate, and tools.

| | Built-in search | maru-deep-pro-search |
|---|---|---|
| **Engines** | 1–2 | **9 + failover** |
| **Ranking** | None | **RRF + BM25 + Granite 97M** |
| **Citations** | Hallucinated / none | **`[N]` + URLs** |
| **Deep-research UI** | None | **Trace · Insights · Clusters** |
| **Cost** | Varies | **$0 · no API keys** |

Quick start & copy-paste prompts: **[GitHub Pages](https://claudianus.github.io/maru-deep-pro-search/)** · full tool/ENV tables in README

---

## 3-minute overview

1. **Install** → `maru-deep-pro-search setup` → restart your agent
2. **General questions** — *“used Galaxy S24 prices 2026”* → `answer`
3. **Code / security / design** — *“FastAPI vs Django 2026 architecture”* → `deep_research` (default 30 sources · 7 subqueries)
4. **Upgrade** — after `pip install -U`, run `update --with-setup` · `setup --check`

---

## ⚡ 10-second install

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**Manual:**
```bash
python3 -m pip install --user maru-deep-pro-search && maru-deep-pro-search setup
```

**Granite 97M (v0.22.1)** — semantic ranking is **always on**. Default model `ibm-granite/granite-embedding-97m-multilingual-r2`. `install.sh` / `setup` run `warmup-embeddings` to **prefetch** weights and reduce first `deep_research` cold start.

```bash
maru-deep-pro-search warmup-embeddings -q
maru-deep-pro-search setup --check
```

**uv:**
```bash
uv tool install --python 3.12 maru-deep-pro-search
```

---

## 🚀 Getting started

```bash
maru-deep-pro-search --version   # 0.22.1
maru-deep-pro-search setup
```

After upgrade:
```bash
pip install -U maru-deep-pro-search
maru-deep-pro-search update --with-setup
maru-deep-pro-search setup --repair
maru-deep-pro-search setup --check
```

Project-local knowledge only:
```bash
maru-deep-pro-search init
```

Claude Code MCP snippet (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "maru-deep-pro-search": {
      "command": "python3",
      "args": ["-m", "maru_deep_pro_search.server"]
    }
  }
}
```

---

## 🏆 vs alternatives

| | maru | Tavily MCP | Perplexity MCP |
|---|---|---|---|
| **Cost** | **$0** | Free tier / paid | $5+/mo |
| **Engines** | **9 + failover** | Single API | Single API |
| **Research enforcement** | **3-layer gate** | ❌ | ❌ |
| **Deep-research UI** | **Trace · Insights** | ❌ | ❌ |

---

## Core MCP tools (top 3)

| Tool | Use |
|------|-----|
| `answer` | Consumer / market / recommendation queries |
| `deep_research` | CVE, architecture, library comparisons (Trace · Insights · Clusters) |
| `fetch_page` | Official docs with sanitization |

**All 18 tools:** [Website #tools](https://claudianus.github.io/maru-deep-pro-search/#tools)

**21-agent matrix:** [agent_matrix.html](https://claudianus.github.io/maru-deep-pro-search/agent_matrix.html)

---

## 📊 Benchmark (TREC-style, 10 queries)

| Metric | Single engine | Multi-engine (maru) |
|--------|---------------|---------------------|
| Precision@5 | baseline | **+86%** |
| NDCG@10 | baseline | **+36%** |
| MRR | baseline | **+25%** |

Trade-off: ~2× latency. Reproduce: `uv run python benchmark/search_quality_benchmark.py`

---

## 🔒 Security (summary)

- 72-pattern prompt-injection sanitization + `fetch_page` EXTERNAL CONTENT wrapper
- `generate_code` blocks code without session citations

Details: [Website #security](https://claudianus.github.io/maru-deep-pro-search/#security)

---

## ⚙️ Configuration

| Variable | Default | Notes |
|----------|---------|-------|
| `MARU_STRICT_QUERY` | `1` | Reject / normalize vague queries |
| `MARU_EMBEDDING_MODEL` | Granite 97M R2 | Semantic rank model |
| `MARU_BENCHMARK_SUITE` | — | `stress` for stress benchmark |

**Full ENV:** [Website #config](https://claudianus.github.io/maru-deep-pro-search/#config)

---

## 🐳 Docker

```bash
docker build -t maru-search .
docker run --rm -i -v $(pwd)/.maru:/app/.maru maru-search
```

---

## Changelog

**v0.22.0–0.22.1:** Mandatory Granite 97M semantic ranking · `warmup-embeddings` · Research Trace / Insights quality pipeline.

Full log: [CHANGELOG.md](CHANGELOG.md)

---

## 🆘 Troubleshooting

| Symptom | Fix |
|---------|-----|
| MCP missing | `setup` then restart agent |
| Slow first search | `warmup-embeddings -q` |
| Config not updated | `update --with-setup` / `setup --repair` |
| Engine failures | `engine_health` · retry later |

---

## 🤝 Contributing · License

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs welcome.

MIT — [LICENSE](LICENSE)
