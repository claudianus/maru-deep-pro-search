<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>Force your AI agent to research before it codes.</strong><br>
  Zero API keys · 9-engine failover · BM25+semantic ranking · Native citations · 20 AI agents
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
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## What it is

`maru-deep-pro-search` is an MCP server that gives your AI coding agent **live web search superpowers** — and forces it to use them before writing any code.

| | Built-in Agent Search | maru-deep-pro-search |
|---|---|---|
| **Engines** | 1–2, no fallback | **9-engine auto-failover** |
| **Ranking** | Raw engine order | **BM25 + semantic + authority/freshness/code-density** |
| **Citations** | Hallucinated or none | **Native `[1]`, `[2]` IDs with real URLs** |
| **Defense** | None | **72-signature prompt injection + zero-width char sanitization** |
| **Enforcement** | "Please search first" (ignored) | **3-layer technical gatekeeping + code validation** |
| **Agents** | Generic | **20 dedicated adapters with skill file injection** |
| **Cost** | Varies | **$0 forever — zero API keys** |

---

## ⚡ 10-Second Install

**macOS / Linux — recommended (auto-installs `uv` if needed):**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**Manual (pip, Python ≥3.10):**
```bash
python3 -m pip install --user "maru-deep-pro-search[semantic]" && maru-deep-pro-search setup
```
`sentence-transformers` is optional. `setup` stays quiet by default; set `MARU_ENABLE_SEMANTIC_INSTALL=1` if you want it to install semantic ranking support.

**Recommended (uv — fastest, includes semantic):**
```bash
uv tool install --python 3.12 --with "sentence-transformers>=3.0.0" git+https://github.com/claudianus/maru-deep-pro-search.git
```
From PyPI only: `uv tool install --python 3.12 "maru-deep-pro-search[semantic]"`.

The setup wizard auto-detects your AI agent, backs up existing configs, injects MCP settings, and enforces research-first rules.

---

## 🚀 Getting Started

### 1. Verify installation
```bash
maru-deep-pro-search --version
# Expected: 0.17.2
```

### 2. Set up your agent
```bash
maru-deep-pro-search setup
```
This auto-detects installed agents (Claude, Cursor, etc.) and injects MCP configs.

### 3. Example MCP config for Claude Code
Add to your `~/.claude/settings.json`:
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

### 4. First research
Ask your agent: *"Latest used Galaxy phone prices"* for `answer()`, or *"Research FastAPI vs Django 2025 architecture"* for `deep_research()` — then the agent synthesizes with real citations.

### 5. Project harness (local data only)

Initialize **repo-local** `.maru/knowledge.db`, `.maru/harness.yaml`, and optional `AGENTS.md`:

```bash
maru-deep-pro-search-init
```

**Agent configs (MCP, rules, skills) are never written inside the repository.** On each machine, run `maru-deep-pro-search setup` once to install into **global** paths (home directory, etc.) — same scope as MCP.

Each clone can commit `.maru/` + `harness.yaml` policy as your team prefers; dotfiles for agents stay out of the repo.

### 6. Search queries & strict gate

Search tools prefer **keyword-style** queries (3–12 terms: product/library + aspect + year), but natural English/Korean questions are normalized first when possible. For example, “갤럭시 중고폰 최신 시세 추천” becomes a current-market search instead of being rejected.

- Disable rejection (optimize only): `export MARU_STRICT_QUERY=0`
- After `deep_research`: receipts live under `~/.maru/receipts/`; **drift** from lockfiles triggers in-tool warnings; call `drift_status` without web I/O.
- Share team cache: `maru-deep-pro-search-knowledge export -o bundle.json` / `import bundle.json`

## 🏆 vs Alternatives

| Feature | maru-deep-pro-search | Tavily MCP | Perplexity MCP |
|---|---|---|---|
| **Cost** | **$0 forever** | Free tier / $0.025 per search | $5/mo minimum |
| **Engines** | **9 scrapers + failover** | 1 API | 1 API |
| **Self-hosted** | **✅** | ❌ | ❌ |
| **Offline capable** | **✅** (cached results) | ❌ | ❌ |
| **Citations** | Native `[N]` | Yes | Yes |
| **Enforces research** | **3-layer technical gate** | ❌ | ❌ |
| **Prompt injection defense** | **72-pattern + semantic** | Basic | Basic |
| **Agent adapters** | **20 agents** | Generic | Generic |

---

## 🛠️ 18 MCP Tools

### Research Core
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `answer` | Perplexity-style answer-engine packet with ranked sources and fetched evidence | General web questions, prices, recommendations, Korean consumer searches |
| `deep_research` | Multi-engine deep search with query expansion, BM25 ranking, **quality score**, and **auto-fetch** | Before code, architecture, security, or complex research |
| `parallel_search` | Run multiple searches simultaneously with comparison mode | Multi-angle analysis (e.g., "vs" comparisons) |
| `web_search` | Scrape + rank + return cited results | Additional targeted sources |
| `search_with_citations` | Pre-numbered sources for academic writing | Papers, documentation requiring strict attribution |

### Fetch & Extract
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `fetch_page` | Extract clean content from a single URL (with 403 auto-stealth fallback) | Reading specific docs found during research |
| `fetch_bulk` | Parallel fetch with deduplication | Reading 2–10 known URLs at once |
| `stealthy_fetch` | Anti-bot bypass for protected sites | Cloudflare/DataDome blocked sites (last resort) |

### Validation & Enforcement
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `generate_code` | **Code validation gate** — blocks un-researched code by checking for missing citations | After research — ensures code is backed by citations |
| `session_state` | Check session research status, tool history, citations | Debugging why a tool was blocked |
| `drift_status` | Manifest/error drift since last research (no web search) | After dependency or error changes |
| `query_knowledge` | Search persisted knowledge base for prior research | Reusing research without re-searching the web |
| `export_research` | Export current session research to a markdown file | Saving/sharing research results |

### Engine & Infrastructure
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `list_engines` | List all search engines with reliability & latency metadata | Choosing the right engine |
| `engine_health` | Real-time circuit breaker status per engine | Diagnosing search failures |
| `cache_stats` | In-memory cache hit/miss statistics | Monitoring performance |
| `clear_caches` | Clear all in-memory caches | Forcing fresh results |
| `version` | Check version & available updates | Verify installation health |

**Tool decision tree:**
```
User request?
├── General web question / latest price / recommendation? → answer(query, mode="balanced")
├── Code / security / architecture / deep research? → deep_research(query, auto_fetch=3)
    ├── Multiple angles? → parallel_search
    ├── Specific URLs? → fetch_page / fetch_bulk
    ├── Blocked site? → stealthy_fetch (last resort)
    ├── Reuse prior research? → query_knowledge
    ├── Check research freshness? → session_state / drift_status
    └── Diagnose slow searches? → cache_stats / engine_health
```

---

## 🤖 20 AI Agents — Extension Mechanism Matrix

One setup injects research-first rules via **every extension surface** each agent offers — hooks, commands, plugins, cron, permissions, and more.

| Agent | MCP | Hooks | Commands | Agents/Cron/Plugins | Rules / Prompts | Skills | Other Surfaces |
|-------|:---:|:-----:|:--------:|:-------------------:|-----------------|--------|----------------|
| **Claude Code** | ✅ | 4 lifecycle hooks | `ask.md` `search.md` `compare.md` `research.md` `verify.md` | — | `CLAUDE.md` + hooks | `~/.claude/skills/` nested | Permissions deny patterns |
| **Cursor** | ✅ | — | `ask.json` `search.json` `compare.json` `research.json` `verify.json` | — | `.cursor/rules/*.md` | `~/.cursor/rules/` flat | `autoEnableTools` |
| **Kimi** | ✅ | `PreToolUse` (TOML) | — | — | `config.toml` `system_prompt` | `~/.kimi/skills/` nested | `default_yolo=false` |
| **Cline** | ✅ | `PreToolUse.py` | — | `maru-research-gate.md` agent + `.cron.md` | `.clinerules/*.md` | `~/.cline/skills/` flat | — |
| **Continue** | ✅ | — | `ask` `search` `compare` `research` `verify` | — | `system_message` + `.continue/rules/` | `~/.continue/rules/` flat | — |
| **Windsurf** | ✅ | 3 Cascade hooks | — | — | `.windsurf/rules/*.md` + `AGENTS.md` | `~/.windsurf/rules/` flat | `.codeiumignore` |
| **Zed** | ✅ | — | — | — | `.rules` + `assistant.md` | — | `tool_permissions` |
| **JetBrains** | ⚠️ | — | — | — | `.idea/ai-assistant-rules/*.md` | `.idea/ai-assistant-rules/` flat | — |
| **Cody** | ⚠️ | — | — | — | `.cody/prompts.md` | — | — |
| **Devin** | ⚠️ | — | — | — | `.devin/rules.md` | — | — |
| **Amazon Q** | ⚠️ | — | — | — | `.amazonq/rules/*.md` | `.amazonq/rules/` flat | — |
| **Tabnine** | ⚠️ | — | — | — | `.tabnine/guidelines/*.md` | `.tabnine/guidelines/` flat | — |
| **Codeium** | ⚠️ | — | — | — | `.codeium/system-prompt.md` | — | — |
| **Copilot** | ⚠️ | — | — | — | `.github/copilot-instructions.md` | — | — |
| **Aider** | ⚠️ | — | — | — | `CONVENTIONS.md` + `.aider.conf.yml` | — | Lint-cmd gate, architect mode |
| **Codex** | ✅ | `codex_hooks` | — | — | `AGENTS.md` + `developer_instructions` | — | `approval_policy` |
| **Kilo** | ✅ | — | — | — | `kilo.jsonc` `systemPrompt` + `instructions` | `~/.config/kilo/rules/` flat | `experimental.codebase_search` |
| **OpenCode** | ✅ | — | — | `maru-research-gate` agent | `AGENTS.md` + `opencode.json` agents | — | — |
| **AntiGravity** | ✅ | — | — | — | `~/.gemini/antigravity/config.json` | — | — |
| **Hermes** | ✅ | Gateway + Shell hooks | — | `maru-research-gate` plugin + cron | `SOUL.md` + `config.yaml` | `~/.hermes/skills/` flat | Plugin system |
| **Supermaven** | ⚠️ | — | — | — | `.supermaven/rules.md` | — | — |

> **Legend:** ✅ = Full MCP support · ⚠️ = Rules only (no native MCP)
>
> **Hooks** = PreToolUse / PostToolUse / SessionStart / pre_write_code / pre_mcp_tool_use / pre_user_prompt / etc.  
> **Commands** = Slash commands or custom commands registered in agent config  
> **Agents/Cron/Plugins** = Custom agents, cron specs, or plugin systems  
> **Skills** = `nested` = `skills/<name>/SKILL.md` · `flat` = `rules/<name>.md`

---

## 🏛️ Architecture

```
MCP Client (Claude, Cursor, Kimi, Windsurf, ...)
        │ JSON-RPC 2.0 / stdio
        ▼
┌──────────────────────────────────────────────────────────────┐
│  maru-deep-pro-search MCP Server                             │
│  ├─ 18 Tools (search, fetch, cite, validate, introspect)     │
│  ├─ 9-Engine Failover Registry (query-aware selection)       │
│  ├─ Hybrid Ranking (BM25 + semantic + authority/freshness)   │
│  ├─ 3-Layer Enforcement + Research Quality Score (A-F)       │
│  ├─ 72-Signature Sanitization + Zero-Width Char Defense      │
│  ├─ SQLite KnowledgeStore (exact → FTS → semantic search)    │
│  ├─ In-Memory TTL Cache (search 5min / fetch 10min)          │
│  └─ Auto Session Pruning + Audit Logging                     │
└──────────────────────────────────────────────────────────────┘
```

### 3-Layer Enforcement

1. **MCP Prompt Injection** — `always_research_first()` routes general questions to `answer` and coding/security work to `deep_research`
2. **Session Gate** — `generate_code()` blocks code generation if no research was done in the session
3. **Agent Rules** — `setup` injects the protocol into **global** per-agent config paths (home, etc.); the official CLI does not write agent dotfiles under the repo root.

The server contains **zero generative LLMs**. Your agent's LLM handles all reasoning and synthesis. The server focuses on search quality: multi-engine coverage, intelligent ranking, and clean content extraction.

### KnowledgeStore

SQLite-backed research cache at `./.maru/knowledge.db`:

- **Deduplication** — Same query hashes to the same entry (UPSERT with access counter)
- **3-tier retrieval** — Exact match → FTS5 full-text → Semantic similarity (optional, local `intfloat/multilingual-e5-small`)
- **Domain stats** — Per-domain success rate and average response time tracking
- **Pruning** — Auto-remove entries older than 30 days

Inspect with `maru-deep-pro-search stats`.

For deep technical details, see [`docs/engine_insights.md`](./docs/engine_insights.md) and [`docs/lessons_learned.md`](./docs/lessons_learned.md).

---

## 📋 Example Outputs

<details>
<summary><b>deep_research</b> — Multi-engine ranked results</summary>

```markdown
## Research: FastAPI vs Django 2025
_engines: duckduckgo_lite, bing, yahoo_
### Sources
#### [1] FastAPI Documentation — fastapi.tiangolo.com
_score: 0.92 | [OFFICIAL-DOCS] | engines: 2 | relevance: 0.89
FastAPI is a modern, fast (high-performance) web framework for building APIs...

#### [2] Django 5.1 Release Notes — docs.djangoproject.com
_score: 0.88 | [OFFICIAL-DOCS] | engines: 2 | relevance: 0.85
Django 5.1 adds async ORM improvements, simplified field choices, and...
```
</details>

<details>
<summary><b>answer</b> — Perplexity-style direct answer</summary>

```markdown
## Answer: What is the best Python web framework in 2025?

**FastAPI** is the dominant choice for API-first services, while **Django** remains king for full-stack applications with admin needs.

**Key differences:**
- Performance: FastAPI is ~3× faster due to async native design [1]
- Ecosystem: Django has 15+ years of plugins and battle-tested ORM [2]
- Learning curve: FastAPI is simpler for API developers; Django requires more upfront investment [3]

**When to choose which:**
- API / microservices → FastAPI
- Full-stack with admin → Django
```
</details>

<details>
<summary><b>generate_code</b> — Validation gate (blocks un-researched code)</b></summary>

```markdown
❌ CODE GENERATION BLOCKED — Research validation failed

Research query: Python asyncio best practices
Research age: 42s

Citations found in your code:
  (none)

ACTION REQUIRED:
1. Run deep_research() on your topic
2. Include [N] citations from research in your code
3. Call generate_code() again with validated code
```
</details>

---

## 🔒 Security

Fetched content is sanitized through a 72-pattern defense layer before reaching your LLM:

- Zero-width character removal (`\u200b`, `\u200c`, `\u200d`)
- Chat-token neutralization (`Human:`, `Assistant:` → `[REDACTED]`)
- MCP-specific attack detection (tool poisoning, rug pulls, shadowing)
- Optional semantic similarity anomaly detection

Every tool call is logged to `.maru/audit.db` with anomaly detection (rapid-fire, oversized results, suspicious params).

See [`SECURITY.md`](./SECURITY.md) for disclosure policy.

---

## ⚙️ Configuration

All optional. Search defaults, timeouts, and retry counts are read in `src/maru_deep_pro_search/config.py` via `SearchConfig.from_env()` → `DEFAULT_CONFIG`, then applied by MCP tool wrappers (`server.py` signatures + `tools.py`) and SERP `with_retry` in engines. (This project does **not** use `pydantic-settings` for that layer.)

| Environment variable | Default | What it controls |
|------------------------|---------|------------------|
| `MARU_SEARCH_ENGINE` | `duckduckgo_lite` | Default `engine` for `web_search`, `search_with_citations`, `answer`, `parallel_search`, `deep_research` |
| `MARU_SEARCH_MAX_RESULTS` | `10` | Default `max_results` / `answer`'s `max_sources` |
| `MARU_SEARCH_MAX_CONCURRENT` | `5` | Default `max_concurrent` for `fetch_bulk` |
| `MARU_SEARCH_RETRIES` | `3` | Max attempts for SERP `with_retry` (e.g. Bing, Yahoo) |
| `MARU_SEARCH_TIMEOUT` | `30.0` | SERP HTML scrape (`web_search`, `search_with_citations`), seconds |
| `MARU_FETCH_HTTP_TIMEOUT` | `20.0` | `fetch_page` / per-URL `fetch_bulk`, seconds |
| `MARU_DEEP_RESEARCH_TIMEOUT` | `45.0` | `deep_research` orchestration, seconds |
| `MARU_ANSWER_TIMEOUT` | `30.0` | `answer` tool, seconds |
| `MARU_AUTO_FETCH_TIMEOUT` | `8.0` | Nested fetch budget inside `deep_research` `auto_fetch`, seconds |
| `MARU_SKIP_UPDATE_CHECK` | (unset) | Any non-empty value skips the startup PyPI update banner |
| `MARU_DEBUG` | (unset) | `1` / `true` / `yes` enables DEBUG logging on the MCP server |

Elsewhere: strict query gate uses `MARU_STRICT_QUERY`; Hermes/Aider session TTL uses `MARU_RESEARCH_TTL` — see earlier sections / agent docs.

---

## 💻 CLI Commands

```bash
# MCP server (stdio transport)
maru-deep-pro-search

# Setup AI agents with MCP config + skill files
maru-deep-pro-search setup
maru-deep-pro-search setup --list
maru-deep-pro-search setup --restore

# Project harness (.maru only — does not touch agent configs in the repo)
maru-deep-pro-search init

# Headless deep research (CI/CD friendly)
maru-deep-pro-search research "FastAPI vs Django 2025" \
  --output report.md --max-sources 8

# Self-update
maru-deep-pro-search update
maru-deep-pro-search update --check
```

---

## 🐳 Docker

```bash
# Build
docker build -t maru-search .

# Run with stdio transport
docker run --rm -i maru-search

# With persistent knowledge store
docker run --rm -i -v $(pwd)/.maru:/app/.maru maru-search
```

---

## 🆘 Troubleshooting

**No results from search engine**
```bash
MARU_SEARCH_ENGINE=bing maru-deep-pro-search
```

**Agent not detected by setup wizard**
```bash
maru-deep-pro-search setup --agents cursor
maru-deep-pro-search setup --list
```

**High memory usage**
```bash
# Use lighter search mode
MARU_SEARCH_MAX_RESULTS=5 maru-deep-pro-search
```

**SKILL.md install shows "unsupported" for my agent**
> That's expected for agents without a skill directory system (e.g., Copilot, JetBrains). Rules are still injected via their native config files. Only agents with official skill support (Cursor, Kimi, Claude, Cline, Continue, Windsurf, Kilo, Tabnine, Hermes) show ✓ for skills.

---

## 🤝 Contributing

PRs welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for development setup, adding engines, and agent adapters.

---

## 📄 License

MIT — see [`LICENSE`](./LICENSE).
