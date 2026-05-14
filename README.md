<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>Force your AI agent to research before it codes.</strong><br>
  Zero API keys · 9-engine failover · BM25+semantic ranking · Native citations · 21 AI agents
</p>

<p align="center">
  <a href="./README.ko.md">🇰🇷 한국어</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/test.yml?style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/test.yml"><img src="https://img.shields.io/badge/coverage-77%25-green?style=flat-square" alt="Coverage"></a>
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
| **Agents** | Generic | **21 dedicated adapters with skill file injection** |
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

**Manual (pip):**
```bash
pip install maru-deep-pro-search[semantic] && maru-deep-pro-search setup
```

The setup wizard auto-detects your AI agent, backs up existing configs, injects MCP settings, and enforces research-first rules.

---

## 🛠️ 10 MCP Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `deep_research` | Multi-engine deep search with query expansion & BM25 ranking | **🔴 ALWAYS FIRST** — before any code, architecture, or technical decision |
| `answer` | Perplexity-style direct answer with inline citations | Quick factual check after research |
| `parallel_search` | Run multiple searches simultaneously with comparison mode | Multi-angle analysis (e.g., "vs" comparisons) |
| `web_search` | Scrape + rank + return cited results | Additional targeted sources |
| `search_with_citations` | Pre-numbered sources for academic writing | Papers, documentation requiring strict attribution |
| `fetch_page` | Extract clean content from a single URL | Reading specific docs found during research |
| `fetch_bulk` | Parallel fetch with deduplication | Reading 2–10 known URLs at once |
| `stealthy_fetch` | Anti-bot bypass for protected sites | Cloudflare/DataDome blocked sites (last resort) |
| `generate_code` | Validate code against research citations | After research — blocks un-researched code |
| `version` | Check version & available updates | Verify installation health |

**Tool decision tree:**
```
Any technical request?
└── deep_research(query) FIRST
    ├── Need quick fact? → answer
    ├── Multiple angles? → parallel_search
    ├── Specific URLs? → fetch_page / fetch_bulk
    └── Blocked site? → stealthy_fetch (last resort)
```

---

## 🤖 21 AI Agents — Extension Mechanism Matrix

One setup injects research-first rules via **every extension surface** each agent offers — hooks, commands, plugins, cron, permissions, and more.

| Agent | MCP | Hooks | Commands | Agents/Cron/Plugins | Rules / Prompts | Skills | Other Surfaces |
|-------|:---:|:-----:|:--------:|:-------------------:|-----------------|--------|----------------|
| **Claude Code** | ✅ | 4 lifecycle hooks | `research.md` `verify.md` | — | `CLAUDE.md` + hooks | `~/.claude/skills/` nested | Permissions deny patterns |
| **Cursor** | ✅ | — | `research.json` `verify.json` | — | `.cursor/rules/*.md` | `~/.cursor/rules/` flat | `autoEnableTools` |
| **Kimi** | ✅ | `PreToolUse` (TOML) | — | — | `config.toml` `system_prompt` | `~/.kimi/skills/` nested | `default_yolo=false` |
| **Cline** | ✅ | `PreToolUse.py` | — | `maru-research-gate.md` agent + `.cron.md` | `.clinerules/*.md` | `~/.cline/skills/` flat | — |
| **Continue** | ✅ | — | `research` `verify` | — | `system_message` + `.continue/rules/` | `~/.continue/rules/` flat | — |
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
┌──────────────────────────────────────────────┐
│  maru-deep-pro-search MCP Server             │
│  ├─ 10 Tools (search, fetch, cite, validate) │
│  ├─ 9-Engine Failover Registry               │
│  ├─ Hybrid Ranking (BM25+semantic)           │
│  ├─ 3-Layer Enforcement                      │
│  ├─ 72-Signature Sanitization                │
│  └─ SQLite KnowledgeStore                    │
└──────────────────────────────────────────────┘
```

### 3-Layer Enforcement

1. **MCP Prompt Injection** — `always_research_first()` prompt forces `deep_research` before any tool call
2. **Session Gate** — `generate_code()` blocks code generation if no research was done in the session
3. **Agent Rules** — Per-agent config files (`.cursorrules`, `CLAUDE.md`, etc.) inject mandatory research protocol

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

All optional. Loaded via `pydantic-settings` with prefix `MARU_SEARCH_`.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGINE` | `duckduckgo_lite` | Default search engine |
| `MAX_RESULTS` | `10` | Results per query per engine |
| `MAX_CONCURRENT` | `5` | Parallel fetch limit |
| `TIMEOUT` | `30.0` | Fetch timeout (seconds) |
| `RETRIES` | `3` | Retry attempts |

---

## 💻 CLI Commands

```bash
# MCP server (stdio transport)
maru-deep-pro-search

# Setup AI agents with MCP config + skill files
maru-deep-pro-search setup
maru-deep-pro-search setup --list
maru-deep-pro-search setup --restore

# Initialize project harness
maru-deep-pro-search init --agents cursor claude

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
