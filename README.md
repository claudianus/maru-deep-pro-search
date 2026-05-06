<p align="center">
  <img src="https://img.shields.io/pypi/v/clco-deep-research-mcp?color=blue&label=PyPI" alt="PyPI">
  <img src="https://img.shields.io/pypi/pyversions/clco-deep-research-mcp?color=green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-purple" alt="License">
  <img src="https://img.shields.io/badge/MCP-native-blue" alt="MCP Native">
  <img src="https://img.shields.io/badge/engines-4-orange" alt="4 Search Engines">
  <img src="https://img.shields.io/badge/cost-free-brightgreen" alt="Free">
</p>

# clco-deep-research-mcp

**The free, coding-agent-optimized deep research MCP that replaces Claude Code's built-in web_search.**

> Claude Code의 `web_search` 툴이 프록시 환경에서 작동하지 않나요? 이 MCP가 완전히 대체합니다. 4개 검색엔진을 직접 스크래핑하고, trafilatura로 본문을 추출하며, 코드 언어/API 시그니처/최신성을 자동 분석합니다. **API 키 불필요, 완전 무료.**

---

## Why This Exists

| Problem | Solution |
|---------|----------|
| Claude Code `web_search` breaks behind proxies | Direct SERP scraping — no API dependencies |
| Existing MCPs return raw HTML or noisy text | trafilatura cleans boilerplate, returns structured markdown |
| Coding agents work with stale docs | htmldate extracts publication dates, freshness warnings |
| "Is this page API reference or a tutorial?" | Auto-classifies content: `[API-REF]` `[TUTORIAL]` `[ERROR-FIX]` |
| LLMs can't tell Python from shell in code blocks | Regex-based 16-language detection + API signature extraction |

## Quick Start

```bash
# One-shot (no install needed)
uvx clco-deep-research-mcp

# Or install globally
pip install clco-deep-research-mcp
clco-deep-research
```

**Claude Code config** (`~/.claude.json`):
```json
{
  "mcpServers": {
    "clco-deep-research": {
      "command": "uvx",
      "args": ["clco-deep-research-mcp"]
    }
  }
}
```

Or use the **[clco-helper](https://github.com/ryankdev/clco-helper)** TUI — one-button install from the MCP management screen.

## Tools (6)

| Tool | Description | Key Feature |
|------|-------------|-------------|
| `web_search` | Scrape 4 search engines directly | Content type hints per result |
| `fetch_page` | Extract clean content from any URL | trafilatura + code-aware metadata |
| `fetch_bulk` | Parallel multi-URL fetch | Quality signals for LLM prioritization |
| `deep_research` | Full pipeline: search → crawl → extract | Quality-sorted, code-aware output |
| `stealthy_fetch` | Full anti-bot bypass | Cloudflare Turnstile, DataDome |
| `parallel_search` | Multiple queries in parallel | Multi-engine scatter-gather |

## Search Engines

| Engine | Fetcher | Speed | Anti-bot | Default |
|--------|---------|-------|----------|---------|
| `duckduckgo_lite` | DynamicFetcher | Fast | No | **Yes** |
| `duckduckgo` | DynamicFetcher | Fast | No | |
| `google` | StealthyFetcher | Medium | Yes | |
| `bing` | DynamicFetcher | Fast | No | |

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  MCP Server (stdio)                │
│                     server.py                      │
├──────────────────────────────────────────────────┤
│  web_search  fetch_page  deep_research  ...       │
│                    tools.py                        │
├──────────────────────────────────────────────────┤
│  duckduckgo.py    │  deep.py  │  extractor.py     │
│  ┌──────────────┐ │           │                    │
│  │ Scrapling     │ │ Pipeline  │  truncate_for_llm │
│  │ DynamicFetcher│ │ orchestr. │  deduplicate_urls │
│  │ StealthyFetch │ │           │  skip_url          │
│  ├──────────────┤ │           │                    │
│  │ trafilatura  │ │           │                    │
│  │ htmldate     │ │           │                    │
│  │ code_aware   │ │           │                    │
│  └──────────────┘ │           │                    │
└──────────────────────────────────────────────────┘
```

### Data Flow

```
Query → scrape_serp() ──→ [SearchResult × N]
  │                            │
  │                   fetch_page(url) × N
  │                            │
  │                   ┌────────┴────────┐
  │                   │ Scrapling fetch  │
  │                   │ trafilatura ext. │
  │                   │ htmldate date    │
  │                   │ code_aware.py    │
  │                   └────────┬────────┘
  │                            │
  └──────────── deep_research() ┘
                      │
              format_for_llm() → LLM-optimized markdown
```

## Code-Aware Metadata

Every fetched page is analyzed for coding-agent relevance:

```markdown
### [1] Async Context Managers in Python [HIGH] (article) [TUTORIAL] [python] [code-heavy 32%] [293d ago]
URL: https://dev.to/...
APIs: async def __aenter__(self):; async def __aexit__(...):; async def main():
```

| Signal | What It Tells the LLM |
|--------|----------------------|
| `[HIGH]` | trafilatura quality score — prioritize this source |
| `[TUTORIAL]` | Content type classification |
| `[python]` | Detected languages from code blocks |
| `[code-heavy 32%]` | Code-to-text ratio — skim vs deep-read |
| `[293d ago]` | Freshness — warn if >1yr stale |
| `APIs:` | Function/class signatures for quick scanning |

## Benchmarks

### vs duckduckgo-websearch (npm MCP, 67KB)

| Metric | duckduckgo-websearch | clco-deep-research |
|--------|---------------------|-------------------|
| Search engines | 1 (DDG API) | 4 (DDG Lite, DDG, Google, Bing) |
| Content extraction | cheerio (basic) | trafilatura (SOTA) |
| Code detection | None | 16 languages |
| API signatures | None | Auto-extracted |
| Date extraction | None | htmldate (95% accuracy) |
| Content freshness | None | Per-page freshness scoring |
| Anti-bot bypass | None | StealthyFetcher (Cloudflare, DataDome) |
| Deep research pipeline | None | Search→Crawl→Extract→Synthesize |
| Package size | 67KB (npm) | ~50KB (Python) |

### Content Extraction Quality

| Source | Scrapling only | trafilatura | Improvement |
|--------|---------------|-------------|-------------|
| realpython.com (tutorial) | 12,890 chars | 45,142 chars | **3.5×** |
| docs.python.org (reference) | 658 chars | 1,967 chars | **3×** |

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| [Scrapling](https://github.com/D4Vinci/Scrapling) | ≥0.2.0 | Browser/HTTP fetching, anti-bot |
| [trafilatura](https://trafilatura.readthedocs.io/) | ≥2.0.0 | Main content extraction (SOTA) |
| [htmldate](https://htmldate.readthedocs.io/) | ≥1.9.4 | Publication date extraction |
| [Pygments](https://pygments.org/) | ≥2.20.0 | Syntax highlighting (reference) |
| [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) | ≥1.0.0 | Model Context Protocol server |

## Roadmap

- [ ] Brave Search API integration (optional higher quality)
- [ ] SearXNG self-hosted search support
- [ ] Page screenshot tool (Playwright)
- [ ] PDF/text file parsing
- [ ] Caching layer for repeated queries
- [ ] Custom search engine plugins

## License

MIT — use it, fork it, ship it. Built for the coding agent era.

---

<p align="center">
  <sub>Made for <a href="https://github.com/ryankdev/clco-helper">clco-helper</a> — the Claude Code power tool</sub>
</p>
