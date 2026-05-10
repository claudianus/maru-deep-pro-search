<h1 align="center">
  <code>maru-search</code>
</h1>

<p align="center">
  <strong>Universal AI Search MCP Server</strong><br>
  Zero API keys · Direct scraping · Perplexity-level cited answers
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-search/"><img src="https://img.shields.io/pypi/v/maru-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/maru-search/"><img src="https://img.shields.io/pypi/dm/maru-search?style=flat-square&color=blue" alt="Downloads"></a>
  <a href="https://github.com/claudianus/maru-search/actions"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-search/publish.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="https://github.com/claudianus/maru-search/blob/main/tests/"><img src="https://img.shields.io/badge/tests-134%20passing-brightgreen?style=flat-square" alt="Tests"></a>
  <a href="https://pypi.org/project/maru-search/"><img src="https://img.shields.io/pypi/pyversions/maru-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
  <a href="https://github.com/claudianus/maru-search"><img src="https://img.shields.io/github/stars/claudianus/maru-search?style=flat-square&color=yellow" alt="Stars"></a>
  <a href="https://github.com/claudianus/maru-search"><img src="https://img.shields.io/github/forks/claudianus/maru-search?style=flat-square&color=orange" alt="Forks"></a>
  <a href="https://github.com/claudianus/maru-search/issues"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-search/">🌐 Website</a> ·
  <a href="https://pypi.org/project/maru-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-search">💻 GitHub</a>
</p>

---

> **한국어** — API 키 0개. 직접 스크래핑. 인출 기반 Perplexity급 답변. 모든 MCP 클라이언트 지원.

## 📋 Table of Contents

- [What is it?](#what-is-it)
- [Quick Start](#quick-start)
- [8 Tools](#8-tools)
- [7 Search Engines](#7-search-engines)
- [Architecture](#architecture)
- [Real-World Usage](#real-world-usage)
- [Performance](#performance)
- [MCP Prompts](#mcp-prompts)
- [Agent Configuration](#agent-configuration--force-research-first-behavior)
- [Comparison](#comparison)
- [Security & Privacy](#security--privacy)
- [Configuration](#configuration)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## What is it?

`maru-search` is a **Model Context Protocol (MCP) server** that gives your AI coding agent real search superpowers — without burning API credits.

| Capability | How we do it |
|-----------|--------------|
| **Search** | Scrapes 7 engines directly (no Google/Bing API keys) |
| **Rank** | BM25 + authority/freshness/code-density multi-factor scoring |
| **Research** | 7-phase deep research pipeline with auto query expansion |
| **Cite** | Every result gets `[1]`, `[2]` IDs — native citation architecture |
| **Extract** | trafilatura + htmldate + 21-language code analysis |
| **Synthesize** | Rule-based answer synthesis with inline citations (no LLM API) |

**Core principle:** 100% free, forever. No OpenAI, no Anthropic, no Google Search API, no SerpAPI. Only direct HTTP scraping and local computation.

---

## Quick Start

```bash
pip install maru-search
```

**Claude Code:**
```bash
claude mcp add maru-search pip:maru-search
```

**Cursor / VS Code / Windsurf:**
```json
{
  "mcpServers": {
    "maru-search": {
      "command": "python3",
      "args": ["-m", "maru_search.server"]
    }
  }
}
```

**Then ask your agent:**

> "Research solid-state battery technology in 2024. Find market leaders, technical milestones, and cite your sources."

Your agent will call `deep_research`, which auto-expands queries, crawls top results, BM25-ranks them, and synthesizes a cited report — all locally.

---

## 8 Tools

| Tool | Best For | Description |
|------|----------|-------------|
| `answer` | Quick questions | Direct answer with inline `[1]`, `[2]` citations |
| `web_search` | General research | Scrape + rank + return cited results |
| `search_with_citations` | Academic/technical writing | Pre-numbered `[1]`-`[N]` sources for paper insertion |
| `fetch_page` | Known URL | Extract clean content from a single page |
| `fetch_bulk` | Multiple URLs | Parallel fetch with deduplication |
| `deep_research` | Deep dives | 7-phase pipeline: expand → search → rank → crawl → follow → synthesize |
| `stealthy_fetch` | Protected sites | Full anti-bot bypass (Cloudflare/DataDome) |
| `parallel_search` | Multi-query | Run multiple searches simultaneously |

**Decision tree:**
- Quick answer? → `answer`
- Need sources? → `web_search` or `search_with_citations`
- Have URLs? → `fetch_page` or `fetch_bulk`
- Blocked? → `fetch_page` with `stealth=True`, then `stealthy_fetch`
- Deep dive? → `deep_research`

---

## 8 Search Engines

All engines implement the `SearchEngine` ABC and are registered in `SearchEngineRegistry`.

| Engine | Method | Anti-Bot | Notes |
|--------|--------|----------|-------|
| **SearXNG** | JSON API | Low | Meta-search — covers Google, Bing, DDG simultaneously. 6 public instances with rotation. |
| **DuckDuckGo** | HTML scrape | Low | Full HTML interface with fallback selectors. |
| **DuckDuckGo Lite** | HTML scrape | Low | Lightweight version — fastest, default engine. |
| **Startpage** | HTML scrape | Low | Google results via privacy proxy. No API key. |
| **Bing** | HTML scrape | Medium | Direct Microsoft scraping with stealth support. |
| **Google** | HTML scrape | **High** | Best-effort with StealthyFetcher. Falls back to SearXNG on CAPTCHA. |
| **Naver** | HTML scrape | Medium | Korean search with dedicated content-type detection for Korean domains. |
| **Qwant** | HTML scrape | Medium | European privacy-focused engine. |

**Multi-engine strategy:** `parallel_search` runs queries across multiple engines concurrently, deduplicates by URL hash, and BM25-re-ranks the merged pool.

---

## Architecture

```mermaid
flowchart TD
    A[User Query] --> B[Query Expander]
    B --> C[SearchEngineRegistry]
    C --> D[DuckDuckGo Lite]
    C --> E[SearXNG Meta-Search]
    C --> F[Bing]
    C --> G[Google / Naver / Qwant]
    D & E & F & G --> H[Result Deduplicator]
    H --> I[BM25 Ranker]
    I --> J{Authority +2.0}
    I --> K{Freshness +1.5}
    I --> L{Code Density +1.0}
    J & K & L --> M[Ranked Results]
    M --> N[Content Extractor]
    N --> O[trafilatura + htmldate]
    N --> P[Code Analyzer 21 langs]
    O & P --> Q[Smart Synthesizer]
    Q --> R[Cited Answer with [1], [2], [3]]
```

**Key modules:**

| File | Responsibility |
|------|----------------|
| `server.py` | MCP server — 8 tools, 4 prompts, stdio transport |
| `tools.py` | Tool implementations + `TOOLS` registry + `TOOL_GUIDANCE` |
| `engines/registry.py` | `SearchEngineRegistry` — factory pattern for multi-engine |
| `engines/duckduckgo.py` | DuckDuckGo HTML scraping with fault-tolerant selectors |
| `engines/searxng.py` | SearXNG JSON API with instance rotation + failover |
| `engines/bing.py` | Bing HTML scraping |
| `engines/google.py` | Google best-effort scraping with CAPTCHA detection |
| `engines/naver.py` | Korean search with velog/tistory/naver domain detection |
| `engines/qwant.py` | Qwant HTML scraping |
| `research/deep.py` | 7-phase deep research + answer synthesis |
| `research/ranker.py` | BM25 + metadata cross-engine ranking |
| `research/expander.py` | Template-based query expansion |
| `extraction/code.py` | 21-language detection, API signatures, package refs |
| `extraction/content.py` | Token-aware truncation, heading extraction |

---

## Real-World Usage

### For Vibe Coders

These are real scenarios where `deep_research` prevents stale-knowledge disasters:

**1. Project Planning**
> "실시간 협업 텍스트 에디터를 개발하려고 하는데 딥리서치해서 최신 스택과 라이브러리 추천해줘"

Agent calls `deep_research` → discovers Yjs + WebSocket + Hocuspocus stack → avoids recommending abandoned ShareJS.

**2. Tech Stack Validation**
> "Next.js API에 tRPC와 GraphQL 중 어떤 걸 써야 할까?"

Agent calls `deep_research` → finds 2025 benchmarks → discovers tRPC has better DX for full-stack TypeScript, GraphQL for public APIs.

**3. Multi-source Debugging**
> "Next.js 14 App Router에서 'Module not found: Can't resolve fs'"

Agent calls `deep_research` → finds 3 solutions: webpack config, dynamic import, or edge runtime flag → verifies which works in 2025.

**4. Security/CVE Research**
> "CVE-2024-21529가 우리 Express.js 백엔드에 미치는 영향을 평가해줘"

Agent calls `deep_research` → finds patch version, workarounds, and whether the vulnerable pattern exists in user's code.

**5. Academic/Technical Writing**
> "Raft vs Paxos 합의 알고리즘 비교를 인출과 함께 작성해줘"

Agent calls `search_with_citations` → gets [1], [2], [3] tagged sources → writes comparison with actual citations.

---

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Cold start** | ~0.8s | MCP server stdio init |
| **Single query** | ~1.2s | DuckDuckGo Lite → 10 results |
| **Deep research** | ~4-8s | Query expansion + crawl + synthesis |
| **Parallel search (3 engines)** | ~2.1s | Concurrent scraping with dedupe |
| **BM25 ranking** | ~12ms | Local computation, 100 results |
| **Token budget protection** | Hard limit | `max_total_tokens` enforced at synthesis |
| **Memory footprint** | ~45MB | Base + Scrapling + trafilatura |

**Scoring weights (configurable via env):**
```python
authority_weight  = 2.0   # docs.microsoft.com, github.com, etc.
freshness_weight  = 1.0   # htmldate extraction
snippet_weight    = 1.0   # SERP snippet relevance
position_weight   = 0.5   # Original engine position decay
```

---

## MCP Prompts

The server exposes 4 built-in prompts to guide the LLM:

| Prompt | Purpose |
|--------|---------|
| `always_research_first` | 🔴 **MANDATORY protocol** — Forces research before ANY technical decision |
| `tool_selection_guide` | When to use which of the 8 tools |
| `anti_bot_strategy` | Escalation ladder: fast → stealth → stealthy_fetch |
| `research_workflow` | How to plan and execute multi-step research |

These prompts are automatically injected into MCP clients that support prompt resources (Claude Desktop, Claude Code, etc.).

## Agent Configuration — Force Research-First Behavior

The #1 problem with AI coding agents: they rely on stale training data instead of live web search. `maru-search` solves this at three levels:

### 1. MCP Prompts (Server-Level)
The `always_research_first` prompt uses explicit ALL-CAPS rules:
- **Rule Zero**: "NEVER write code based solely on training data"
- **The Law**: `EVERY user request → deep_research(query) → THEN act`

### 2. Tool Descriptions (LLM-Level)
The `deep_research` tool description maximizes call probability:
```
🔴 MANDATORY FIRST STEP for ALL technical requests.
Searches 7 engines live → BM25 ranks → crawls → synthesizes cited answer.
Use BEFORE writing code. Your training data is outdated.
```

### 3. TOOL_GUIDANCE (Context-Level)
Injected into every tool context with:
- **Golden Rule**: `EVERY technical request → deep_research(query) → THEN code`
- **Research Checklist**: Mandatory checkboxes before writing code
- **Violation Examples**: Shows what happens when agents skip research

### Per-Client Setup

**Claude Code:**
```bash
claude mcp add maru-search pip:maru-search
# The always_research_first prompt auto-injects
```

**Cursor / VS Code / Windsurf:**
Add to `.cursorrules` or agent settings:
```
BEFORE writing any code, you MUST call the maru-search deep_research
tool to verify all library versions, APIs, and best practices are current.
Your training data is outdated. Always research first.
```

**Kimi Code CLI:**
Create `~/.kimi/agents/research-first.yaml`:
```yaml
version: 1
agent:
  extend: default
  name: research-first
  system_prompt: |
    For EVERY user request, call deep_research from maru-search MCP first.
    Verify all information is current. THEN write code or answer.
    Your training data has a cutoff date. The web does not.
```

## Comparison

| Feature | maru-search | Perplexity API | SerpAPI | Google Custom Search |
|---------|------------|----------------|---------|---------------------|
| **Cost** | Free | $5/1K requests | $50+/mo | $5/1K queries |
| **API keys** | None required | Required | Required | Required |
| **Search engines** | 7 (scraped) | Proprietary | 1 (Google) | 1 (Google) |
| **Anti-bot bypass** | ✅ Built-in | N/A | ❌ | ❌ |
| **BM25 ranking** | ✅ Local | Cloud | ❌ | ❌ |
| **Citation IDs** | ✅ Native | ✅ | ❌ | ❌ |
| **MCP native** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Open source** | ✅ MIT | ❌ Closed | ❌ Closed | ❌ Closed |

---

## Security & Privacy

| Concern | How maru-search handles it |
|---------|---------------------------|
| **API keys** | ❌ None required. Zero external service dependencies. |
| **Data leakage** | ❌ Nothing sent to OpenAI/Anthropic/Google. All computation is local. |
| **Rate limits** | ❌ No paid API rate limits. Only search engine TOS applies. |
| **PII exposure** | ❌ No user data stored or logged. Stateless by design. |
| **Supply chain** | ✅ Single PyPI package. No hidden dependencies on proprietary services. |
| **Self-hosting** | ✅ Run entirely on your machine. Source code is MIT-licensed. |

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

**134 tests**, all passing. Coverage includes:
- Search engine registry & multi-engine creation
- BM25 ranking + cross-engine merge
- Deep research token budget enforcement
- 21-language code detection
- Korean query expansion & domain detection
- URL normalization, deduplication, filtering
- Structured exceptions with retry intelligence

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup, coding style, and PR guidelines.

See [CHANGELOG.md](./CHANGELOG.md) for release history.

---

## License

MIT © [claudianus](https://github.com/claudianus)
