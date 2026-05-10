<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>Force your AI agent to research before it codes.</strong><br>
  Zero API keys · Direct scraping · Citation-native answers
</p>

<p align="center">
  <a href="./README.ko.md">🇰🇷 한국어</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/publish.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/tests/"><img src="https://img.shields.io/badge/tests-174%20passing-brightgreen?style=flat-square" alt="Tests"></a>
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-deep-pro-search/">🌐 Website</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## One-liner Install

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

Or with pip:
```bash
pip install maru-deep-pro-search && maru-deep-pro-search setup
```

The setup wizard auto-detects your AI agent (Claude Code, Cursor, Kimi, Windsurf, etc.), backs up existing configs, injects MCP settings, and enforces research-first rules.

---

## What it does

Your AI coding agent has a critical flaw: it answers from stale training data. `maru-deep-pro-search` fixes this by giving your agent live web search superpowers — and **forcing it to use them first**.

| Capability | How |
|-----------|-----|
| **Search** | Scrapes 7 engines directly. No API keys. |
| **Rank** | BM25 + authority/freshness/code-density scoring |
| **Research** | 7-phase deep research pipeline with auto query expansion |
| **Cite** | Every result gets `[1]`, `[2]` IDs — native citation architecture |
| **Enforce** | Setup CLI injects mandatory research-first rules into your agent |

**Core principle:** 100% free, forever. No OpenAI, no Anthropic, no Google Search API, no SerpAPI.

---

## 8 Tools

| Tool | Purpose |
|------|---------|
| `answer` | Quick answer with inline citations |
| `web_search` | Scrape + rank + return cited results |
| `search_with_citations` | Pre-numbered sources for academic writing |
| `fetch_page` | Extract clean content from a single URL |
| `fetch_bulk` | Parallel fetch with deduplication |
| `deep_research` | 7-phase pipeline: expand → search → rank → crawl → synthesize |
| `stealthy_fetch` | Anti-bot bypass for protected sites |
| `parallel_search` | Run multiple searches simultaneously |

**Decision tree:**
- Quick answer? → `answer`
- Need sources? → `web_search` or `search_with_citations`
- Deep dive? → `deep_research`
- Blocked? → `stealthy_fetch`

---

## Configuration

All environment variables are optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `MARU_SEARCH_ENGINE` | `duckduckgo_lite` | Default engine |
| `MARU_SEARCH_MAX_RESULTS` | `10` | Results per query |
| `MARU_SEARCH_MAX_CONCURRENT` | `5` | Parallel fetch limit |
| `MARU_SEARCH_MAX_TOKENS_SOURCE` | `2500` | Token budget per source |
| `MARU_SEARCH_MAX_TOKENS_TOTAL` | `20000` | Total output token budget |
| `MARU_SEARCH_TIMEOUT` | `30.0` | Fetch timeout (seconds) |
| `MARU_SEARCH_RETRIES` | `3` | Retry attempts |

---

## Testing

```bash
pytest tests/ -v
```

174 tests, all passing.

---

## License

MIT © [claudianus](https://github.com/claudianus)
