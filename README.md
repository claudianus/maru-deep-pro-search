<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>Force your AI agent to research before it codes.</strong><br>
  Zero API keys · Direct scraping · Citation-native · Semantic hybrid ranking · Smart fallback
</p>

<p align="center">
  <a href="./README.ko.md">🇰🇷 한국어</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/test.yml?style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/lint.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/lint.yml?style=flat-square&label=lint" alt="Lint"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/publish.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/publish.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
  <a href="#docker"><img src="https://img.shields.io/badge/Docker-ready-blue?style=flat-square&logo=docker" alt="Docker"></a>
  <a href="#security"><img src="https://img.shields.io/badge/security-72%20signatures-red?style=flat-square&logo=shield" alt="Security"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-deep-pro-search/">🌐 Website</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## 📑 Table of Contents

- [Design Principles](#design-principles)
- [One-liner Install](#one-liner-install)
- [What it does](#what-it-does)
  - [vs Alternatives](#vs-alternatives)
- [Why built-in search isn't enough](#why-your-agents-built-in-web-search-isnt-enough)
- [Architecture](#architecture)
- [Real Enforcement Architecture](#real-enforcement-architecture)
- [8 Tools](#8-tools)
- [How It Works](#how-it-works)
- [Technical Deep Dives](#technical-deep-dives)
- [Docker](#docker)
- [Security](#security)
- [For Researchers](#for-researchers)
- [Performance Tips](#performance-tips)
- [Performance](#performance-characteristics)
- [Quick Reference](#quick-reference)
- [Configuration](#configuration-reference)
- [Before & After](#before--after)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Tech Stack](#tech-stack)
- [Testing](#testing)
- [Contributing](#contributing)
- [Acknowledgments](#acknowledgments)
- [Related Projects](#related-projects)
- [Citation](#citation)
- [Star History](#star-history)

---

## Design Principles

These principles guide every design decision in the project:

1. **Zero API keys, forever** — No OpenAI, no Anthropic, no SerpAPI, no Bing API. Direct scraping and local computation only.
2. **Failover by default** — Single points of failure are unacceptable. 9 engines, automatic escalation, graceful degradation.
3. **Citation-native** — Every claim must be traceable. Sources are first-class citizens, not afterthoughts.
4. **Research-first enforcement** — The agent MUST search before coding. Rules are injected, not suggested.
5. **Defense in depth** — Prompt injection defense isn't a checkbox. 72 signatures, multi-language, MCP-specific attacks.
6. **Transparency by default** — Audit every tool call. Log everything. Let users inspect the system.
7. **Batteries included, swappable** — Works out of the box with sensible defaults, but every component is replaceable.

---

## One-liner Install

> **Prerequisite:** Python **≥3.10** (the install script handles this automatically)

**macOS / Linux — recommended (auto-installs uv if needed):**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows (PowerShell) — recommended:**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**Manual install (pip):**
```bash
# Make sure Python 3.10+ is already on your PATH
pip install maru-deep-pro-search[semantic] && maru-deep-pro-search setup
```

The setup wizard auto-detects your AI agent (Claude Code, Cursor, Kimi, Windsurf, Zed, JetBrains AI, Supermaven, etc.), backs up existing configs, injects MCP settings, and enforces research-first rules. The `[semantic]` extra installs `sentence-transformers>=3.0.0` for dense vector ranking.

---

## What it does

Your AI coding agent has a critical flaw: it answers from stale training data. `maru-deep-pro-search` fixes this by giving your agent live web search superpowers — and **forcing it to use them first**.

| Capability | How |
|-----------|-----|
| **Search** | Scrapes 9 engines directly via async HTTP. No API keys. |
| **Rank** | BM25 + dense semantic similarity + authority/freshness/code-density scoring |
| **Research** | 7-phase deep research pipeline with auto query expansion, smart fetch, and gap detection |
| **Cite** | Every result gets `[1]`, `[2]` IDs — native citation architecture |
| **Enforce** | 3-layer real enforcement: server-side session gating + client-side hooks (PreToolUse, lint-cmd, onPreEdit) + protocol injection for 21 agents |
| **Persist** | Harness platform stores project knowledge in SQLite with optional semantic embeddings |
| **Audit** | SQLite-backed MCP tool call logging with anomaly detection |
| **Sandbox** | Docker sandbox for isolated execution |

**Core principle:** 100% free, forever. No OpenAI, no Anthropic, no Google Search API, no SerpAPI, no Bing API. Only direct scraping and local computation.

### vs Alternatives

| | maru-deep-pro-search | Perplexity API | Built-in Agent Search | SerpAPI |
|---|:---:|:---:|:---:|:---:|
| **Price** | Free | $5/1K calls | Free (limited) | $50+/mo |
| **API keys** | None required | Required | Varies | Required |
| **Engines** | 9 + failover | 1 (internal) | 1-2 | 1 at a time |
| **Citations** | Native `[1]` IDs | Yes | Rare | No |
| **Ranking** | BM25 + semantic + metadata | Proprietary | None | None |
| **Prompt injection defense** | 72 signatures | Unknown | None | None |
| **Audit logging** | Built-in | No | No | No |
| **Self-hostable** | Yes | No | No | No |
| **MCP-native** | Yes | No | Partial | No |

---

## Why your agent's built-in web search isn't enough

Modern AI coding agents ship with "web search" tools. They sound convenient — until you actually rely on them.

### The problem with built-in search

| Built-in Web Search | Reality |
|---------------------|---------|
| **Single engine** | If DuckDuckGo blocks the request, you're dead in the water. No fallback. |
| **Raw results** | Returns whatever the search engine spits out. No ranking, no quality filtering. |
| **No citations** | The agent hallucinates sources or simply makes them up. |
| **Shallow fetch** | Grabs a snippet and calls it a day. Misses critical API docs, version tables, code examples. |
| **Zero defense** | Fetches arbitrary web pages with no protection against prompt injection, zero-width chars, or malicious content. |
| **Passive** | The agent *can* search, but nothing forces it to. It still defaults to stale training data. |

### What maru-deep-pro-search does differently

This isn't a standalone search tool. It's a **search MCP server with harness setup tools** — it provides the search/fetch tools and injects the research-first rules into your agent.

- **9-engine failover** — DuckDuckGo (HTML + Lite), Bing, Google, Yahoo, Ecosia, Baidu, Startpage, Naver. One fails? The next one picks up instantly.
- **Perplexity-grade ranking** — BM25 relevance + semantic similarity + authority / freshness / code-density scoring. The best sources float to the top.
- **Native citations** — Every claim gets `[1]`, `[2]`, `[3]`. Sources are real, traceable, and injected into the response.
- **Deep research pipeline** — Auto query expansion → multi-angle search → smart fetch with anti-bot escalation → gap detection → synthesized cited answer.
- **Content quality analysis** — Detects code-heavy pages, API docs, stale content, and authority signals. Prioritizes official documentation over random blogs.
- **Prompt injection defense** — Sanitizes fetched content: strips zero-width chars, neutralizes chat tokens, flags suspicious patterns.
- **Research-first enforcement** — The setup CLI injects mandatory rules into your agent: "You MUST call deep_research before writing ANY code." No exceptions.
- **Zero API keys** — 100% free, forever. No OpenAI, no Anthropic, no SerpAPI, no Bing API.

**Bottom line:** Built-in search gives your agent a browser. `maru-deep-pro-search` gives it a research team with a chief-of-staff that forces them to use it.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         MCP Client Layer                              │
│  (Claude Code, Cursor, Zed, JetBrains, Cody, Devin, Amazon Q,         │
│   Tabnine, Codeium, Kimi, Windsurf, Aider, Copilot, Cline,            │
│   Hermes, Continue, Supermaven, OpenCode, Kilo, AntiGravity)            │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ JSON-RPC 2.0 / stdio
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      maru-deep-pro-search                             │
│                          MCP Server                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ 4 Prompts    │  │ 8 Tools      │  │ TOOL_GUIDANCE            │   │
│  │ (always_     │  │              │  │ (context-level rules)    │   │
│  │  research_   │  │              │  │                          │   │
│  │  first, ...) │  │              │  │                          │   │
│  └──────────────┘  └──────┬───────┘  └──────────────────────────┘   │
│                           │                                          │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Research Pipeline                               │
│                                                                       │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐    │
│  │ Query       │──▶│ 10 Engines  │──▶│ Result Merge &          │    │
│  │ Expander    │   │ (async)     │   │ Fuzzy Deduplication     │    │
│  │ (templates  │   │ Registry    │   │ (Jaccard + semantic)    │    │
│  │ + synonyms) │   │ pattern)    │   │                         │    │
│  └─────────────┘   └─────────────┘   └───────────┬─────────────┘    │
│                                                  │                   │
│  ┌───────────────────────────────────────────────┘                   │
│  ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Hybrid Ranking Engine                                         │   │
│  │  • BM25: k1=1.5, b=0.75 on title + snippet (rank-bm25)        │   │
│  │  • Metadata: authority × freshness × code_density             │   │
│  │  • Semantic: cos_sim(query, text) via multilingual-e5-small   │   │
│  │    (33M params, 384-dim, 100+ languages, MTEB 59.3)           │   │
│  │  • Final: weighted ensemble with engine confidence            │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┘                                        │
│  ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Smart Fetch Layer                                             │   │
│  │  • Network probe (DuckDuckGo RTT) → adaptive timeout          │   │
│  │  • Domain history filter (slow>5s or fail>80% → skip)         │   │
│  │  • Priority queue: authority domains first                    │   │
│  │  • Error-type-aware strategy:                                 │   │
│  │    DNS/Network → skip | SSL → stealth retry | 403→stealth    │   │
│  │  • Scrapling session reuse (AsyncDynamicSession pool)         │   │
│  │    disable_resources=True, block_ads=True, timeout in ms      │   │
│  │  • Early abort: stop when 3 HIGH quality results obtained     │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┘                                        │
│  ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Content Extraction Pipeline                                   │   │
│  │  • trafilatura: main text + metadata extraction               │   │
│  │  • htmldate: publish date detection                           │   │
│  │  • code.py: 21-language syntax detection, API extraction      │   │
│  │  • sanitize.py: zero-width char removal, chat token           │   │
│  │    neutralization, suspicious pattern flagging                │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┘                                        │
│  ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Synthesis & Citation                                          │   │
│  │  • Rule-based synthesis (zero LLM in server)                  │   │
│  │  • Native [1], [2], [3] citation IDs                          │   │
│  │  • Gap detection for incomplete research                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

The server contains **zero generative LLMs**. Synthesis is rule-based; your agent's LLM handles reasoning. Optional semantic scoring uses an embedding model (bi-encoder only, no generation).

---

## 🔒 Real Enforcement Architecture

> **This is not prompt injection.** Previous "enforcement" was just text appended to system prompts — LLMs can ignore text. This is **technical gatekeeping** with three independent layers.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: Tool Dependency Gate                      │
│  Code generation tools require a research_id parameter that must      │
│  match a valid, completed research session. No ID → no code.          │
├──────────────────────────────────────────────────────────────────────┤
│                    LAYER 2: Client-Side Hooks                         │
│  • Claude Code: PreToolUse hook (exit 2) blocks Write/Edit            │
│  • Aider: lint-cmd gate script fails if research incomplete           │
│  • Cursor: .cursorrules + custom /research, /verify slash commands    │
│  • Hermes: pre_tool_call plugin hook blocks un-researched tools       │
│  Physical blocking — the agent CANNOT proceed even if it wants to.    │
├──────────────────────────────────────────────────────────────────────┤
│                    LAYER 1: Server-Side Enforcement                   │
│  SessionEnforcer tracks every MCP session. Gated tools                │
│  (fetch_page, web_search, answer, ...) return a hard error            │
│  with exit code if deep_research hasn't been called first.            │
│  Research expires after 30 minutes — stale research is rejected.      │
└──────────────────────────────────────────────────────────────────────┘
```

### How Each Layer Works

**Layer 1 — Server-side (`SessionEnforcer`)**
- Every MCP connection gets a `session_id`
- `deep_research()` marks the session with a `research_id` + timestamp + citations
- `web_search`, `answer`, `fetch_page` 등은 **자유롭게 사용 가능** — research 없이도 호출됨
- `generate_code(research_id=...)`만 세션의 `research_id` 일치 여부를 검증
- Research TTL: 30 minutes (configurable via `MARU_RESEARCH_TTL` env var)

**Layer 2 — Client-side Hooks**

| Agent | Hook Type | Mechanism | Block Action |
|-------|-----------|-----------|-------------|
| **Claude Code** | `PreToolUse` + `PostToolUse` + `SessionStart` | Pre blocks Bash; Post detects Write/Edit bypass (GH#13744 workaround); SessionStart injects protocol | Exit 2 blocks Bash; PostToolUse reverts un-researched edits |
| **Aider** | `lint-cmd` + `test-cmd` | Python gate script in `~/.maru/aider_research_gate.py` inserted as **first** lint/test command | Lint/test failure aborts edit + `auto-test: true` enforces test pass |
| **Cursor** | `.cursorrules` + commands + **hooks** | Custom `/research` and `/verify` slash commands + `.cursor/hooks/onPreEdit` gate script (2026+) | Rules + MCP auto-enable + onPreEdit veto |
| **Hermes** | `pre_tool_call` plugin | Python plugin via `hermes_agent.plugins` entry point | Hook returns block action |
| **Others** | Protocol injection | `RESEARCH_PROTOCOL` injected into agent config | Best-effort (Layer 1 enforces) |

**Layer 3 — Tool Dependency (`generate_code`)**
- `generate_code(research_id=..., proposed_code=...)` requires a valid `research_id` from `deep_research`
- `proposed_code` must contain at least one citation `[N]` from the research result
- Returns detailed validation report on failure (missing citations, research_id mismatch, expired research)

### Why Three Layers?

A single layer can be bypassed:
- **Prompt-only** → LLM ignores it (proven by our audit)
- **Server-only** → Agent could call tools directly without MCP
- **Client-only** → Agent could use a different client

Three layers with different trust boundaries means an attacker must compromise **server + client + tool contract** simultaneously.

---

## 8 Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| `answer` | Quick answer with inline citations | Simple factual questions |
| `web_search` | Scrape + rank + return cited results | Need ranked sources |
| `search_with_citations` | Pre-numbered sources for academic writing | Documentation, papers |
| `fetch_page` | Extract clean content from a single URL | Known source deep-dive |
| `fetch_bulk` | Parallel fetch with deduplication | Multiple known URLs |
| `deep_research` | Full 7-phase pipeline with gap detection | Complex technical questions |
| `stealthy_fetch` | Anti-bot bypass for protected sites | Blocked by Cloudflare/etc |
| `parallel_search` | Run multiple searches simultaneously | Comparative analysis |

**Decision tree:**
- Quick answer? → `answer`
- Need sources? → `web_search` or `search_with_citations`
- Deep dive? → `deep_research`
- Blocked? → `stealthy_fetch`

### Example: Deep Research in Action

```python
from maru_deep_pro_search.tools import deep_research

result = deep_research(
    "What are the security implications of using pickle in Python production code?",
    max_total_tokens=15000,
)

print(f"Query: {result.query}")
print(f"Engine used: {result.engine}")
print(f"Sources found: {result.total_sources}")
print(f"High quality: {result.high_quality_count}")
print(f"Time: {result.elapsed_ms:.0f}ms")
print(f"\n{result.synthesized_answer}")
```

**Typical output:**

```
Query: What are the security implications of using pickle in Python production code?
Engine used: duckduckgo_lite → searxng (failover)
Sources found: 12
High quality: 5
Time: 4.2s

Using Python's `pickle` module in production carries significant security risks:

**Arbitrary Code Execution (ACE)** [1][3][5]
`pickle` deserializes by executing Python code. A malicious payload can execute any command:
```python
# NEVER do this with untrusted data
data = pickle.loads(untrusted_bytes)  # 💥 RCE vulnerability
```

**Safer Alternatives** [2][4]
- `json` — text-only, no code execution (recommended for APIs)
- `msgpack` — binary, fast, no code execution [2]
- `protobuf` — schema-enforced, language-agnostic [4]

**When pickle is acceptable** [3]
- Internal caches with signed/encrypted payloads
- Fully controlled environments with no untrusted input

---
Sources:
[1] Python docs — pickle module security (docs.python.org, 2024)
[2] msgpack.org — Serialization format comparison (2023)
[3] OWASP — Insecure Deserialization Cheat Sheet (owasp.org, 2024)
[4] Google — Protocol Buffers documentation (developers.google.com, 2024)
[5] CVE-2024-XXXX — Python pickle remote code execution (cve.mitre.org)
```

This is what your AI agent sees after calling `deep_research` — a cited, synthesized answer with real sources, not hallucinated claims.

---

## How It Works

When your agent calls `deep_research`, here's what happens under the hood:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Query       │────▶│  2. Expand      │────▶│  3. Search      │
│  Parse          │     │  Subqueries     │     │  10 Engines     │
│                 │     │                 │     │  (parallel)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐     ┌────────▼────────┐
│  7. Synthesize  │◀────│  6. Gap Detect  │◀────│  5. Deep Fetch  │
│  Cited Answer   │     │  Missing Info   │     │  + Extract      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         ▲                                              │
         └──────────────────────────────────────────────┘
                    4. Rank & Deduplicate
```

**Phase 1: Query Parsing** — Detects query intent (factual, technical, comparative, temporal) and selects the optimal engine strategy.

**Phase 2: Query Expansion** — Generates 3-5 subqueries from templates and synonyms. A query about "Express.js security" becomes:
- "Express.js security best practices 2024"
- "Express.js CVE vulnerabilities"
- "express helmet middleware configuration"

**Phase 3: Parallel Search** — Dispatches subqueries to up to 9 engines concurrently, capped at 3 simultaneous connections via Semaphore. First 3 results returned abort the rest.

**Phase 4: Hybrid Ranking** — BM25 relevance × semantic similarity × authority × freshness × code-density. Best sources float to the top.

**Phase 5: Smart Fetch** — Fetches full page content with anti-bot escalation (HTTP → stealth → Playwright). Extracts clean text with trafilatura.

**Phase 6: Gap Detection** — Analyzes fetched content for missing information. If no code examples found, triggers a targeted "code example" subquery.

**Phase 7: Synthesis** — Combines sources into a cited answer with `[1]`, `[2]` IDs. Every claim is traceable.

**Total time:** ~3-8 seconds for typical queries.

---

## Technical Deep Dives

### Query Expansion Engine

Before hitting any search engine, the original query is expanded using a template-based system:

- **Templates**: `"{query} tutorial"`, `"{query} best practices"`, `"{query} documentation"`, `"{query} github"`, `"{query} vs alternative"`
- **Synonym injection**: Technical terms get expanded with common aliases (e.g., "docker compose" → "docker-compose")
- **Language awareness**: Korean queries get Korean-specific templates (e.g., `"{query} 사용법"`, `"{query} 예제"`)
- **Output**: 5–7 expanded queries per original, executed in parallel across all engines

### Multi-Engine Search Layer

Nine search engines are supported, all via direct scraping or open APIs:

| Engine | Method | Notes |
|--------|--------|-------|
| DuckDuckGo (lite) | HTML scrape | Default, fastest |
| DuckDuckGo (html) | HTML scrape | Fallback with JS support |
| Bing | HTML scrape | Locale-pinned (`en-US`) |
| Google | Stealth session reuse | Anti-bot evasion, lowest rate limit risk |
| Yahoo | HTML scrape | Redirect decoding |
| Ecosia | HTML scrape | Organic-only filtering |
| Baidu | HTML scrape | Noise-filtered (`result-op` exclusion) |
| Startpage | JS-rendered proxy | Google via privacy proxy |
| Naver | HTML scrape (SSR) | Obfuscated DOM recovery |

**Registry pattern**: `SearchEngineRegistry` uses a factory with `_instances` dict for singleton reuse. Engines requiring stealth use `AsyncStealthySession` for browser reuse, dramatically reducing rate limit hits vs. spawning a new browser per request.

**Rate limiting**: Three-layer defense prevents 429 storms:
1. `asyncio.Semaphore(3)` caps concurrent searches in `deep_research`
2. `EngineRateLimiter` enforces per-engine cooldowns (Google/Startpage: 3s, Baidu: 2s, others: 1–1.5s), auto-wrapped via `__init_subclass__`
3. `TokenBucket` provides optional global QPS throttling

**Parallel execution**: `asyncio.gather()` across all configured engines. Results are merged and deduplicated before ranking.

### Hybrid Ranking Algorithm

The ranking engine combines four signals into a weighted ensemble:

```
final_score = bm25_score      × 0.35
            + authority_score × 0.20
            + freshness_score × 0.15
            + code_density    × 0.10
            + semantic_score  × 0.20   (if sentence-transformers installed)
```

**BM25** (`rank-bm25`, k1=1.5, b=0.75): Computed over title + snippet corpus. BM25 is a probabilistic retrieval function that scores documents based on term frequency and inverse document frequency, with saturation and length normalization.

**Authority scoring**:
- Domain whitelist bonus: `github.com`, `docs.python.org`, `developer.mozilla.org`, etc. get +0.3
- TLD scoring: `.edu`, `.gov`, `.ac.kr` get +0.2; `.blog`, `.medium` get -0.1
- Path depth penalty: deeper paths (e.g., `/a/b/c/d`) get slightly lower scores

**Freshness scoring** (`htmldate`):
- Extracts publish date from HTML metadata
- Exponential decay: `score = exp(-days_old / 365)`
- Undated pages get neutral score (0.5)

**Code density** (`pygments`):
- Tokenizes content with language-appropriate lexer
- `code_density = code_tokens / total_tokens`
- Technical queries boost pages with high code density

**Semantic scoring** (optional, `sentence-transformers>=3.0.0`):
- Model: `intfloat/multilingual-e5-small` (33M parameters, 384 dimensions, 100+ languages, MIT license, MTEB 59.3)
- Why this model: replaces `all-MiniLM-L6-v2` (EN-only, 2021) with modern multilingual support including Korean
- Cosine similarity between query embedding and page text embedding (first 300 chars)
- Batch processing for efficiency
- **Not a generative LLM**: embedding-only bi-encoder. No factual reasoning, no hallucination risk.
- Cross-encoder was evaluated and removed: marginal gains (<2%) not worth 3× latency increase

**Deduplication**:
- URL-level exact dedup (normalized via `urllib.parse`)
- Fuzzy dedup: Jaccard similarity on title + snippet (threshold 0.72)
- Semantic fallback dedup: cosine similarity >0.95 for near-duplicate detection

### Smart Fetch & Resilience

The fetch layer is designed for production-grade reliability:

**Network probe** (`_probe_network()`):
- Measures DuckDuckGo RTT on every `deep_research` call
- Adjusts `timeout_per_fetch` and `max_sources` based on latency
- Slow network (>5s RTT): reduces concurrency, increases timeouts

**Domain history** (`KnowledgeStore.domain_stats`):
- SQLite table tracking per-domain `avg_duration_ms`, `failure_rate`, `last_updated`
- Slow domains (>5s average) are preemptively skipped
- Unreliable domains (>80% failure rate) are blacklisted
- Updated after every fetch attempt

**Error-type-aware handling**:

| Error | Strategy |
|-------|----------|
| DNS / Network unreachable | Skip domain immediately |
| SSL certificate error | Retry with `AsyncStealthySession` |
| HTTP 403 / 429 | Retry with stealth + reduced concurrency |
| HTTP 404 | Skip |
| Timeout | Retry once with increased timeout (+3s) |
| CAPTCHA (Google only) | Flag and skip |

**Scrapling optimizations**:
- `AsyncDynamicSession` with `disable_resources=True`, `block_ads=True`
- Session reuse via `_get_session()` — single session per engine instance
- `timeout` parameter is in **milliseconds** (converted via `int(timeout * 1000)`)
- Built-in retry: `retries=2`, `retry_delay=1`

**Early abort**:
- `asyncio.as_completed()` with `max_concurrent=5`
- Stops when 3 `HIGH` quality results (trafilatura extraction + content_length > 200) are obtained
- Proper Task cancellation in `finally` block to prevent dangling coroutines

### Content Extraction Pipeline

```
Raw HTML
    │
    ▼
┌─────────────────┐
│ trafilatura     │ → main text, title, metadata
│ (main content)  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│htmldate│ │ code.py  │
│(date)  │ │(syntax)  │
└────────┘ └──────────┘
    │         │
    ▼         ▼
┌─────────────────┐
│ sanitize.py     │ → safe for LLM injection
│ (defense layer) │
└─────────────────┘
```

**trafilatura**: Extracts main content from HTML, removing navigation, ads, sidebars. Returns clean markdown-like text.

**htmldate**: Heuristic date extraction from HTML metadata, JSON-LD, and content analysis.

**code.py**: 21-language syntax detection using Pygments lexers. Extracts API signatures, function names, and code blocks for code-density scoring.

**sanitize.py**: Prompt injection defense layer:
- Zero-width character removal (`\u200b`, `\u200c`, `\u200d`, `\ufeff`)
- Chat token neutralization: sequences like `Human:`, `Assistant:`, `System:` are replaced with `[REDACTED]`
- Suspicious pattern detection: excessive repetition (>50% of content), base64 blobs (>1KB), unicode homoglyphs
- All sanitization happens **before** LLM context injection

### Semantic Search (Optional)

The optional semantic module adds dense vector similarity without any generative capabilities:

- **Model**: `intfloat/multilingual-e5-small`
  - 33M parameters, 384-dimensional embeddings
  - 100+ languages including Korean, Japanese, Chinese
  - MIT license (commercial use allowed)
  - MTEB score: 59.3 (vs all-MiniLM-L6-v2's 56.3)
- **Architecture**: Bi-encoder only. Query and document are encoded independently, similarity is cosine distance.
- **No Cross-Encoder**: Was evaluated and removed. Cross-encoder added ~800ms latency for <2% relevance improvement. Bi-encoder + BM25 hybrid is sufficient.
- **Lazy loading**: Model loads on first use via `_LazyModels` singleton. CPU-only.
- **Graceful degradation**: If `sentence-transformers` is not installed, all semantic branches silently skip with zero runtime errors.

Install: `pip install maru-deep-pro-search[semantic]`

### Harness Platform

Project-level knowledge persistence for long-running research workflows:

**KnowledgeStore** (SQLite):
- `pages`: extracted content with full-text search (FTS5)
- `domain_stats`: per-domain performance tracking
- `semantic_embeddings`: optional vector storage for similarity search
- `projects`: project metadata and configuration

**WorkflowEngine** (7-phase generator):
1. **Probe**: Network health check
2. **Expand**: Query expansion
3. **Search**: Multi-engine parallel search
4. **Rank**: Hybrid ranking + deduplication
5. **Fetch**: Smart fetch with domain filtering
6. **Extract**: Content extraction + sanitization
7. **Synthesize**: Rule-based answer + citation + gap detection

**CLI commands**:
```bash
maru-deep-pro-search init          # Initialize .maru/ in current directory
maru-deep-pro-search setup         # Configure AI agent integration
maru-deep-pro-search stats         # KnowledgeStore health & statistics
maru-deep-pro-search workflow      # Generate GitHub Actions CI/CD workflow
```

### Citation Architecture

Native citation IDs are assigned **before** synthesis, ensuring every claim can be traced:

1. Search results are collected from all engines
2. URL deduplication + fuzzy deduplication
3. Hybrid ranking produces final ordering
4. Sequential IDs `[1]`, `[2]`, `[3]` are assigned based on final rank
5. Synthesis references these stable IDs
6. LLM receives pre-numbered sources, preventing hallucinated citations

The `search_with_citations` tool returns sources in academic format with URLs, titles, and publish dates.

---

## Docker

Run the MCP server in a sandboxed container (recommended for production):

```bash
# Build
docker build -t maru-search .

# Run with stdio transport (for Claude Desktop, Cursor, etc.)
docker run --rm -i maru-search

# Run with SSE transport on port 8000
docker run --rm -p 8000:8000 maru-search --transport sse

# With volume for persistent knowledge store
docker run --rm -i -v $(pwd)/.maru:/app/.maru maru-search
```

**Docker Compose (recommended for persistent deployments):**

```bash
# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The Dockerfile uses a **non-root user**, includes a health check, and ships with `uv` for fast dependency resolution. This aligns with MCP security best practices for sandboxing untrusted tool executions.

---

## Security

### Prompt Injection Defense

`sanitize.py` implements a **72-pattern multi-layer defense** against prompt injection and tool poisoning:

| Layer | What it does |
|-------|-------------|
| **Character-level** | Removes zero-width chars (`\u200b`, `\u200c`, `\u200d`), control chars, neutralizes chat tokens |
| **Signature detection** | 72 regex patterns across 10+ languages (EN/KO/ZH/JA/RU/ES/FR/DE/AR/PT) |
| **MCP-specific** | Detects tool poisoning, rug pulls, shadowing, MPMA, cross-tool poisoning, unauthorized invocation |
| **Embedding-based** | Optional semantic similarity detector using `sentence-transformers` |
| **Content wrapping** | All fetched content is wrapped in `[EXTERNAL CONTENT]` blocks with risk metadata |

### Audit Logging

`harness/audit.py` provides behavioral monitoring for tool invocations:

- Logs every tool call (name, params, result size, duration)
- **Anomaly detection**: rapid-fire (>5 in 5s), unusually large results, suspicious parameters, slow execution (>30s)
- Per-tool rolling statistics for baseline comparison
- Stored in `.maru/audit.db` (SQLite)

Reference: Implements recommendations from Huang et al. (2026) *"Are AI-assisted Development Tools Immune to Prompt Injection?"* (arXiv:2603.21642v1).

---

## For Researchers

Research queries (papers, arxiv, citations, DOI) are handled by the general web search engines with optimized ranking. The hybrid ranking engine naturally prioritizes authoritative academic sources:

- **Authority scoring** gives `.edu`, `.ac.kr`, `arxiv.org`, `semanticscholar.org` a significant boost
- **Freshness scoring** prioritizes recent publications
- **Code density** detection surfaces papers with implementation details

```bash
# For research-heavy queries, increase source count
MARU_SEARCH_MAX_RESULTS=20 MARU_SEARCH_ENGINE=duckduckgo_lite

# Or use search_with_citations for academic-style pre-numbered sources
```

**Example queries that work well:**
- "Latest transformer architecture papers 2024"
- "ArXiv 2401.12345 citation count"
- "Semantic Scholar attention mechanism survey"
- "Compare BERT vs GPT-4 tokenization approaches"

---

## Performance Tips

### For faster research
```bash
# Use the lite engine (faster, less blocked)
MARU_SEARCH_ENGINE=duckduckgo_lite

# Reduce concurrent fetches on slow networks
MARU_SEARCH_MAX_CONCURRENT=2

# Lower token budget for quicker answers
MARU_SEARCH_MAX_TOKENS_TOTAL=8000
```

### For better results
```bash
# Enable semantic ranking (requires sentence-transformers)
pip install maru-deep-pro-search[semantic]

# Use academic engine for research queries
MARU_SEARCH_ENGINE=academic

# Increase quality threshold
MARU_SEARCH_MIN_QUALITY_RESULTS=5
```

### For CI/CD pipelines
```bash
# Disable semantic model to save memory
MARU_SEARCH_SEMANTIC=false

# Use Docker for reproducible runs
docker run --rm -i maru-search
```

---

## Performance Characteristics

| Metric | Target | Implementation |
|--------|--------|----------------|
| Cache hit (KnowledgeStore) | <100ms | SQLite FTS5 + indexed domain_stats |
| Full `deep_research` | <10s | 9 engines, Semaphore(3) concurrent cap, early abort at 3 HIGH results |
| Scrapling session startup | ~0ms (amortized) | Single session reused per engine instance |
| Semantic model load | ~2s (first call only) | Lazy init, CPU-only |
| Memory footprint | ~150MB base, +120MB with semantic | No GPU required |

---

## Quick Reference

### CLI Commands

```bash
# Setup (auto-detect agents)
maru-deep-pro-search setup

# Setup specific agents
maru-deep-pro-search setup --agents cursor claude

# List detected agents
maru-deep-pro-search setup --list

# Check config status
maru-deep-pro-search setup --check

# Restore from backup
maru-deep-pro-search setup --restore

# Initialize project harness
maru-deep-pro-search init --path .

# Show knowledge stats
maru-deep-pro-search stats

# Generate CI workflow
maru-deep-pro-search workflow

# Run MCP server
maru-deep-pro-search
```

### Per-Agent Setup Summary

| Agent | Command | Enforcement | Key Files |
|-------|---------|-------------|-----------|
| **Claude Code** | `setup --agents claude` | `PreToolUse` + `PostToolUse` + `SessionStart` | `~/.claude/hooks/maru_research_gate.py`, `~/.claude/settings.json` |
| **Aider** | `setup --agents aider` | `lint-cmd` + `test-cmd` gate (14 languages) | `~/.maru/aider_research_gate.py`, `.aider.conf.yml` |
| **Cursor** | `setup --agents cursor` | `onPreEdit` hook + `/research` command | `.cursor/hooks/onPreEdit`, `.cursorrules`, `.cursor/settings.json` |
| **Hermes** | `setup --agents hermes` | `pre_tool_call` plugin | `~/.hermes/plugins/maru-research/`, `~/.hermes/config.yaml` |
| **Windsurf** | `setup --agents windsurf` | `defaultInstructions` + `autoEnableTools` + MCP | `~/.codeium/windsurf/mcp_config.json`, `~/.windsurf/settings.json` |
| **Zed** | `setup --agents zed` | `context_servers` (MCP) + `assistant.md` + tool_permissions | `~/.config/zed/settings.json`, `~/.config/zed/assistant.md` |
| **Continue** | `setup --agents continue` | Custom `/research` + `/verify` commands | `~/.continue/config.json` |
| **JetBrains** | `setup --agents jetbrains` | `mcp.autoEnableTools` | `.idea/mcp.json` |
| **Copilot** | `setup --agents copilot` | `defaultInstructions` | VS Code `settings.json` |
| **Cline** | `setup --agents cline` | `defaultInstructions` | VS Code `settings.json` |
| **Devin** | `setup --agents devin` | Config injection | `~/.devin/devin.json` |
| **Amazon Q** | `setup --agents amazonq` | Config injection | `~/.amazonq/amazonq.json` |
| **Cody** | `setup --agents cody` | Config injection | `~/.cody/cody.json` |
| **Codeium** | `setup --agents codeium` | Config injection | `~/.codeium/codeium.json` |
| **Codex** | `setup --agents codex` | TOML `mcp_servers` + `developer_instructions` + `AGENTS.md` | `~/.codex/config.toml`, `AGENTS.md` |
| **Supermaven** | `setup --agents supermaven` | Config injection | `~/.supermaven/supermaven.json` |
| **Tabnine** | `setup --agents tabnine` | Config injection | `~/.tabnine/tabnine.json` |
| **OpenCode** | `setup --agents opencode` | Config injection | `~/.opencode/opencode.json` |
| **Kimi** | `setup --agents kimi` | Config injection | `~/.kimi/config` |
| **Kilo** | `setup --agents kilo` | Config injection | `~/.kilo/kilo.json` |
| **AntiGravity** | `setup --agents antigravity` | Config injection | `~/.antigravity/antigravity.json` |

> **Physical blocking** (Claude, Aider, Cursor, Hermes) prevents edits even if the agent ignores prompts. **Protocol injection** (others) relies on Layer 1 server enforcement as the hard backstop.

### Environment Variables

```bash
MARU_SEARCH_ENGINE=duckduckgo_lite        # Default engine
MARU_SEARCH_MAX_RESULTS=10                # Results per query
MARU_SEARCH_MAX_CONCURRENT=5              # Parallel fetch limit
MARU_SEARCH_MAX_TOKENS_TOTAL=20000        # Total token budget
MARU_SEARCH_TIMEOUT=30.0                  # Fetch timeout (s)
MARU_SEARCH_RETRIES=3                     # Retry attempts
MARU_SEARCH_SEMANTIC=true                 # Enable semantic ranking
```

---

## Configuration Reference

All environment variables are optional. Runtime config is loaded via `pydantic-settings` with env prefix `MARU_SEARCH_`.

| Variable | Default | Description |
|----------|---------|-------------|
| `MARU_SEARCH_ENGINE` | `duckduckgo_lite` | Default search engine |
| `MARU_SEARCH_MAX_RESULTS` | `10` | Results per query per engine |
| `MARU_SEARCH_MAX_CONCURRENT` | `5` | Parallel fetch limit |
| `MARU_SEARCH_MAX_TOKENS_SOURCE` | `2500` | Token budget per extracted source |
| `MARU_SEARCH_MAX_TOKENS_TOTAL` | `20000` | Total output token budget |
| `MARU_SEARCH_TIMEOUT` | `30.0` | Fetch timeout (seconds) |
| `MARU_SEARCH_RETRIES` | `3` | Retry attempts for transient failures |
| `MARU_SEARCH_STEALTH_TIMEOUT` | `15.0` | Stealth session timeout (seconds) |
| `MARU_SEARCH_MIN_QUALITY_RESULTS` | `3` | Early abort threshold for HIGH quality results |

---

## Before & After

| | Before | After |
|---|---|---|
| **Agent answers** | From stale 2023 training data | From live web search with freshness scoring |
| **Sources** | None, hallucinated | `[1]`, `[2]` with real URLs and publish dates |
| **Setup** | Manual MCP config per agent | One-liner auto-detects all 21 agents |
| **Enforcement** | Prompt-only (ignored by LLM) | 3-layer: server gate + client hooks + protocol injection |
| **Cost** | $5–50/mo API fees | **$0 forever** |
| **Ranking** | Raw engine ordering | BM25 + semantic + metadata hybrid |
| **Resilience** | Single point of failure | 9-engine failover + smart fallback |
| **Persistence** | Stateless | Project-level SQLite knowledge store |

---

## Known Limitations

| Limitation | Why | Workaround |
|------------|-----|------------|
| **Search engines may block scrapers** | Google, Bing aggressively rate-limit scrapers | 9-engine failover + 3-layer rate limiting handles this automatically |
| **Semantic model loads slowly on first use** | `sentence-transformers` initializes on demand | ~2s one-time cost; stays warm afterwards |
| **No JavaScript rendering by default** | Most engines use static HTTP fetch | Use `stealthy_fetch` tool for JS-heavy sites |
| **KnowledgeStore is local-only** | SQLite per project, no cloud sync | Mount `.maru/` directory in Docker for persistence |
| **Rate limits on stealth engines** | Google/Startpage have aggressive rate limits | 3-layer rate limiting (Semaphore + cooldowns + session reuse) mitigates this |
| **Some sites block all scrapers** | Cloudflare, captcha, bot detection | Stealth fetcher helps but can't guarantee access |
| **Korean content quality varies** | Naver blocks non-browser requests | Fallback to DuckDuckGo Korean results |

---

## Troubleshooting

### Module not found after install
```bash
# Make sure you're using Python 3.10+
python3 --version

# If using uv, ensure the venv is active
source .venv/bin/activate

# Reinstall
uv pip install -e ".[semantic]"
```

### Search engine returns no results
```bash
# Try a different engine
MARU_SEARCH_ENGINE=bing maru-deep-pro-search

# Check network connectivity
curl -I https://duckduckgo.com

# Enable debug logging
MARU_SEARCH_DEBUG=1 maru-deep-pro-search
```

### Agent not detected by setup wizard
```bash
# Manually specify the agent
maru-deep-pro-search setup --agent cursor

# List supported agents
maru-deep-pro-search setup --list-agents
```

### Docker container exits immediately
```bash
# Check logs
docker logs maru-deep-pro-search

# Run interactively for debugging
docker run --rm -it maru-search bash
```

### High memory usage
The semantic ranking model loads on first use and stays in memory:
```bash
# Disable semantic ranking (pure BM25)
MARU_SEARCH_SEMANTIC=false maru-deep-pro-search

# Or use the lite variant
MARU_SEARCH_ENGINE=duckduckgo_lite
```

---

## FAQ

**Q: Do I need any API keys?**  
A: No. Zero API keys required. The search engines are scraped directly via HTTP.

**Q: Which Python versions are supported?**  
A: Python 3.10, 3.11, 3.12, and 3.13.

**Q: Does it work on Windows?**  
A: Yes. Use the PowerShell install script or `pip install`.

**Q: Can I use it without Docker?**  
A: Absolutely. Docker is optional for sandboxed deployments.

**Q: How do I add support for my favorite AI agent?**  
A: See [CONTRIBUTING.md](./CONTRIBUTING.md). You need to implement 3 methods: `detect()`, `install()`, and `inject_rules()`.

**Q: Is the knowledge store shared between projects?**  
A: No. Each project gets its own `.maru/knowledge.db` in the project root.

**Q: What happens when all 9 engines fail?**  
A: The system returns an error with a suggested fallback engine. In practice, this is extremely rare due to the geographic diversity of the engine endpoints.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Scraping** | scrapling, trafilatura, htmldate |
| **Ranking** | rank-bm25, sentence-transformers (optional) |
| **MCP Protocol** | mcp>=1.0.0 |
| **Configuration** | pydantic-settings |
| **Persistence** | SQLite + FTS5 |
| **Build** | uv, setuptools |
| **Testing** | pytest, pytest-asyncio, pytest-cov |
| **Linting** | ruff, mypy |
| **CI/CD** | GitHub Actions |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest --cov=src/maru_deep_pro_search --cov-report=term-missing

# Run specific module tests
pytest tests/test_sanitize.py -v        # Security signatures
pytest tests/test_research.py -v        # Deep research pipeline
pytest tests/test_engines.py -v         # Search engines
pytest tests/test_harness.py -v         # Harness persistence
```

202 tests, all passing. Coverage includes unit tests for all 9 engines, ranking algorithms, content extraction, sanitization, harness persistence, rate limiting, and integration tests for the full research pipeline.

---

## Contributing

PRs welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for:
- Development setup with `uv`
- Adding new search engines or agent adapters
- Adding security signatures
- Release process (automated via GitHub Actions — no manual PyPI pushes)

See [CHANGELOG.md](./CHANGELOG.md) for release history and [ROADMAP.md](./ROADMAP.md) for upcoming features.

Please read our [Code of Conduct](./CODE_OF_CONDUCT.md), [Security Policy](./SECURITY.md), and [LICENSE](./LICENSE) before participating.

### Development quickstart

```bash
# Install with dev dependencies
make install

# Run tests
make test

# Run linter
make lint

# Format code
make format
```

---

## Acknowledgments

- **[trafilatura](https://trafilatura.readthedocs.io/)** — Core content extraction engine
- **[scrapling](https://github.com/D4Vinci/scrapling)** — Async web scraping framework
- **[rank-bm25](https://github.com/dorianbrown/rank_bm25)** — BM25 ranking implementation
- **[sentence-transformers](https://sbert.net/)** — Semantic similarity models
- **Huang et al. (2026)** — MCP security research that informed our 72-signature defense layer

---

## Related Projects

| Project | What it does | How it complements |
|---------|-------------|-------------------|
| [Perplexity](https://www.perplexity.ai/) | AI search with citations | Cloud-based alternative; maru is self-hosted and free |
| [SearXNG](https://docs.searxng.org/) | Self-hosted meta search | Inspiration for multi-engine design; maru adds ranking, citations, MCP |
| [trafilatura](https://trafilatura.readthedocs.io/) | Web content extraction | Core dependency; maru adds MCP integration and research pipeline |
| [scrapeghost](https://github.com/jamesturk/scrapeghost) | LLM-powered scraping | Alternative approach; maru uses deterministic scraping + ranking |
| [browser-use](https://github.com/browser-use/browser-use) | Browser automation for AI | Complementary: maru for search, browser-use for complex interactions |

---

## Citation

If you use `maru-deep-pro-search` in your research or publications, please cite:

```bibtex
@software{maru_deep_pro_search,
  title = {maru-deep-pro-search: Perplexity-grade web research MCP server},
  author = {claudianus},
  year = {2025},
  url = {https://github.com/claudianus/maru-deep-pro-search},
  version = {0.9.2}
}
```

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=claudianus/maru-deep-pro-search&type=Date)](https://star-history.com/#claudianus/maru-deep-pro-search&Date)

---

## License

MIT © [claudianus](https://github.com/claudianus)
