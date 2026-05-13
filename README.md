<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>Force your AI agent to research before it codes.</strong><br>
  Zero API keys · 9-engine failover · BM25+semantic ranking · Native citations
</p>

<p align="center">
  <a href="./README.ko.md">🇰🇷 한국어</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/test.yml?style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-deep-pro-search/">🌐 Website</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## What it is

`maru-deep-pro-search` is an MCP server that gives your AI coding agent **live web search superpowers** — and forces it to use them before writing any code.

| | Built-in Agent Search | maru-deep-pro-search |
|---|---|---|
| **Engines** | 1–2, no fallback | 9-engine auto-failover |
| **Ranking** | Raw engine order | BM25 + semantic + authority/freshness/code-density |
| **Citations** | Hallucinated or none | Native `[1]`, `[2]` IDs with real URLs |
| **Defense** | None | 72-signature prompt injection + zero-width char sanitization |
| **Enforcement** | "Please search first" (ignored) | 3-layer technical gatekeeping |
| **Cost** | Varies | **$0 forever** — zero API keys |

---

## Install

**macOS / Linux — recommended (auto-installs `uv` if needed):**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**Manual (pip):**
```bash
pip install maru-deep-pro-search[semantic] && maru-deep-pro-search setup
```

The setup wizard auto-detects your AI agent, backs up existing configs, injects MCP settings, and enforces research-first rules.

---

## Quick Start

```python
from maru_deep_pro_search.tools import deep_research

result = deep_research(
    "What are the security implications of using pickle in Python?",
    max_sources=5
)
print(result)  # ranked URLs with metadata — agent decides which to fetch
```

**MCP tool decision tree:**
- Quick answer? → `answer`
- Need ranked sources? → `web_search`
- Deep dive? → `deep_research`
- Blocked by bot protection? → `stealthy_fetch`

See [`AGENTS.md`](./AGENTS.md) for per-agent setup details.

---

## Architecture

```
MCP Client (Claude, Cursor, Kimi, Windsurf, ...)
        │ JSON-RPC 2.0 / stdio
        ▼
┌──────────────────────────────────────┐
│  maru-deep-pro-search MCP Server     │
│  ├─ 10 Tools (search, fetch, cite)  │
│  ├─ 9-Engine Failover Registry      │
│  ├─ Hybrid Ranking (BM25+semantic)  │
│  ├─ 3-Layer Enforcement             │
│  └─ SQLite KnowledgeStore           │
└──────────────────────────────────────┘
```

The server contains **zero generative LLMs**. Your agent's LLM handles all reasoning and synthesis. The server focuses on search quality: multi-engine coverage, intelligent ranking, and clean content extraction.

For deep technical details, see [`docs/engine_insights.md`](./docs/engine_insights.md) and [`docs/lessons_learned.md`](./docs/lessons_learned.md).  
For execution-learned insights, see [`AGENTS.md`](./AGENTS.md).

---

## 10 Tools

| Tool | Purpose |
|------|---------|
| `answer` | Quick answer with inline citations |
| `web_search` | Scrape + rank + return cited results |
| `search_with_citations` | Pre-numbered sources for academic writing |
| `fetch_page` | Extract clean content from a single URL |
| `fetch_bulk` | Parallel fetch with deduplication |
| `deep_research` | Deep multi-engine search with ranked URLs + metadata |
| `stealthy_fetch` | Anti-bot bypass for protected sites |
| `parallel_search` | Run multiple searches simultaneously |

---

## Security

Fetched content is sanitized through a 72-pattern defense layer before reaching your LLM:

- Zero-width character removal (`\u200b`, `\u200c`, `\u200d`)
- Chat-token neutralization (`Human:`, `Assistant:` → `[REDACTED]`)
- MCP-specific attack detection (tool poisoning, rug pulls, shadowing)
- Optional semantic similarity anomaly detection

Every tool call is logged to `.maru/audit.db` with anomaly detection (rapid-fire, oversized results, suspicious params).

See [`SECURITY.md`](./SECURITY.md) for disclosure policy.

---

## Configuration

All optional. Loaded via `pydantic-settings` with prefix `MARU_SEARCH_`.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGINE` | `duckduckgo_lite` | Default search engine |
| `MAX_RESULTS` | `10` | Results per query per engine |
| `MAX_CONCURRENT` | `5` | Parallel fetch limit |
| `TIMEOUT` | `30.0` | Fetch timeout (seconds) |
| `RETRIES` | `3` | Retry attempts |

---

## CLI Commands

```bash
# MCP server (stdio transport)
maru-deep-pro-search

# Setup AI agents with MCP config
maru-deep-pro-search setup
maru-deep-pro-search setup --list
maru-deep-pro-search setup --restore

# Initialize project harness
maru-deep-pro-search init --agents cursor claude

# Manage plugins
maru-deep-pro-search-plugin list
maru-deep-pro-search-plugin install <git-url>

# Headless deep research (CI/CD friendly)
python -m maru_deep_pro_search.server research "FastAPI vs Django 2025" \
  --output report.md --max-sources 8
```

---

## Docker

```bash
# Build
docker build -t maru-search .

# Run with stdio transport
docker run --rm -i maru-search

# With persistent knowledge store
docker run --rm -i -v $(pwd)/.maru:/app/.maru maru-search
```

---

## Troubleshooting

**No results from search engine**
```bash
MARU_SEARCH_ENGINE=bing maru-deep-pro-search
```

**Agent not detected by setup wizard**
```bash
maru-deep-pro-search setup --agent cursor
maru-deep-pro-search setup --list-agents
```

**High memory usage**
```bash
# Use lighter search mode
MARU_SEARCH_MAX_RESULTS=5 maru-deep-pro-search
```

---

## Contributing

PRs welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for development setup, adding engines, and agent adapters.

---

## License

MIT — see [`LICENSE`](./LICENSE).
