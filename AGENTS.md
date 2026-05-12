# Agent Instructions for maru-deep-pro-search

> **CRITICAL REMINDER**: PyPI deployment is handled **automatically by GitHub Actions**. Do NOT attempt manual PyPI uploads via `twine`.

## Deployment Workflow

### PyPI Publishing (AUTOMATED)

The project uses **GitHub Actions** to deploy to PyPI automatically:

- **Trigger**: Push a git tag starting with `v` (e.g., `v0.5.0`)
- **Workflow**: `.github/workflows/publish.yml`
- **Method**: Uses `PYPI_API_TOKEN` secret if available, falls back to trusted publishing

**To release a new version:**

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit and push to main
git add -A && git commit -m "feat: v0.5.0 - description"
git push origin main

# 4. Create and push a version tag (this triggers PyPI deployment)
git tag v0.5.0
git push origin v0.5.0
```

**What happens next:**
1. GitHub Actions workflow `publish.yml` triggers automatically
2. Builds sdist and wheel with `uv build`
3. Publishes to PyPI with `uv publish` (token or trusted publishing)
4. Package appears on https://pypi.org/project/maru-deep-pro-search/

### DO NOT

- ❌ Run `twine upload` manually
- ❌ Run `twine upload` manually
- ❌ Attempt direct uploads from local machine

### GitHub Pages Deployment

GitHub Pages is automatically deployed from the `docs/` directory on every push to `main`. The site is a single static HTML file (`docs/index.html`) — no build step needed.

## Version Bump Checklist

Before creating a new release tag:

- [ ] Update `version` in `pyproject.toml`
- [ ] Update `CHANGELOG.md` with new version section
- [ ] Update version badge in `docs/index.html` (hero badge)
- [ ] Update test count in `docs/index.html` if changed
- [ ] Update test count in `README.md` if changed
- [ ] Update test count in `AGENTS.md` if changed
- [ ] Update engine list in `AGENTS.md` if engines added/removed
- [ ] Run full test suite: `pytest tests/ -v` (all must pass)
- [ ] Commit all changes
- [ ] Push to `main`
- [ ] Create and push version tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
- [ ] Verify GitHub Actions workflow succeeds
- [ ] Verify PyPI page shows new version

## Project Structure Reminders

```
src/maru_deep_pro_search/
├── __init__.py            # Version info
├── server.py              # MCP server + prompts (8 tools)
├── tools.py               # 8 MCP tools + TOOL_GUIDANCE + TOOLS registry
├── config.py              # Runtime configuration
├── exceptions.py          # Structured exception hierarchy
├── engines/               # Search engine implementations + registry (9 active)
│   ├── base.py            # SearchEngine ABC, cooldown wrapping, shared helpers
│   ├── registry.py        # SearchEngineRegistry (factory pattern)
│   ├── duckduckgo.py      # DuckDuckGoEngine (default, SSR)
│   ├── duckduckgo_lite.py # DuckDuckGo Lite fallback
│   ├── bing.py            # BingEngine (locale-pinned HTML scrape)
│   ├── google.py          # GoogleEngine (session-reuse stealth)
│   ├── yahoo.py           # YahooEngine (redirect decoding)
│   ├── ecosia.py          # EcosiaEngine (organic results)
│   ├── baidu.py           # BaiduEngine (noise-filtered Chinese search)
│   ├── startpage.py       # StartpageEngine (JS-rendered Google proxy)
│   └── naver.py           # NaverEngine (obfuscated DOM recovery)
├── extraction/            # Content extraction utilities
│   ├── code.py            # 21-language detection, API extraction
│   └── content.py         # truncate_for_llm, headings, token estimation
├── research/              # Deep research pipeline
│   ├── deep.py            # Deep research + answer synthesis + citations
│   ├── expander.py        # Query expansion (template-based)
│   ├── ranker.py          # BM25 + semantic hybrid cross-engine ranking
│   ├── semantic_ranker.py # Bi-Encoder dense vector similarity (optional)
│   └── gap_detector.py    # Research gap detection
├── harness/               # Project-level knowledge persistence & workflow
│   ├── persistence.py     # KnowledgeStore (SQLite + semantic search)
│   ├── project.py         # init_project(), HarnessProject
│   └── workflow.py        # WorkflowEngine with 7-phase generator
└── utils/                 # URL, retry utilities
    ├── retry.py           # Exponential backoff with jitter
    └── url.py             # URL normalization, filtering, deduplication
```

## Testing

Always run tests before committing:

```bash
source .venv/bin/activate
pytest tests/ -v
```

**Current requirement**: 202 tests, all passing.

## Key Architecture Decisions

1. **100% FREE — No external paid APIs ever** — This is the core principle. All search, ranking, extraction, and synthesis must work with zero API keys. No OpenAI, no Anthropic, no Google Search API, no Bing API. Only direct scraping and local computation.
2. **No manual PyPI uploads** — GitHub Actions handles this
3. **Trusted publishing** — Modern secure PyPI authentication (no tokens)
4. **uv for build/publish** — Fast, reliable Python packaging
5. **Tag-based releases** — Semantic versioning via git tags
6. **Engine registry pattern** — `SearchEngineRegistry` enables multi-engine support (all free scrapers)
7. **BM25 + metadata ranking** — Perplexity-level result quality using only local computation
8. **Citation-native output** — All results include citation IDs [1], [2] without external services
9. **Research-first enforcement** — MCP prompts, tool descriptions, and TOOL_GUIDANCE are all designed to FORCE the agent to research before coding. See below.
10. **Prompt injection defense** — All fetched content is sanitized before LLM injection (zero-width chars removed, chat tokens neutralized, suspicious patterns flagged and replaced).
11. **Semantic hybrid ranking** — Optional `sentence-transformers` integration adds dense vector similarity on top of BM25 for significantly better relevance. Falls back gracefully when not installed.
12. **Smart fallback engine** — Error-type-aware responses (dns/network/ssl/blocked/not_found) with per-type strategy. Stealth auto-retry, network health probe, domain history filter.
13. **Harness platform** — Project-level knowledge persistence (`KnowledgeStore`) and structured workflow engine (`WorkflowEngine`) for research-coding loops.
14. **Three-layer rate limiting** — `asyncio.Semaphore(3)` (concurrency cap) + `EngineRateLimiter` (per-engine cooldowns, auto-wrapped via `__init_subclass__`) + `TokenBucket` (global QPS). Prevents 429 storms on Google/Baidu.
15. **Session-reuse stealth** — Google/Startpage use `AsyncStealthySession` (browser reuse + cookie persistence) instead of `StealthyFetcher` (new browser per call). Dramatically reduces rate limit hits.
16. **Obfuscated DOM resilience** — Naver's hashed CSS classes (`sds-comps-*`) bypassed via SSR container detection. Baidu's AI widgets filtered via `result-op` class exclusion.

## Forcing Agents to Research Before Coding

The #1 problem with AI coding agents: they rely on stale training data instead of live web search. `maru-deep-pro-search` solves this at the MCP server level through three enforcement mechanisms:

### 1. MCP Prompts (Server-Level)

The server exposes 4 prompts via `prompts/list` and `prompts/get`:

| Prompt | Purpose |
|--------|---------|
| `always_research_first` | 🔴 **MANDATORY protocol** — Forces the agent to call `deep_research` before ANY technical decision |
| `tool_selection_guide` | Updated to emphasize `deep_research` as the mandatory first step |
| `anti_bot_strategy` | Escalation ladder for blocked sites |
| `research_workflow` | Phase 0 = mandatory `deep_research` before coding |

**How it works:** MCP clients (Claude Desktop, Claude Code, etc.) that support prompt resources will load these prompts into context. The `always_research_first` prompt uses explicit ALL-CAPS rules like "NEVER write code based solely on training data".

### 2. Tool Descriptions (LLM-Level)

The `deep_research` tool description is written to maximize the LLM's probability of calling it first:

```
🔴 MANDATORY FIRST STEP for ALL technical requests.
Searches 9 engines live → BM25 ranks → crawls → synthesizes cited answer.
Use BEFORE writing code, proposing architecture, or making technical claims.
Your training data is outdated. This tool searches the LIVE web.
```

Other tools are tagged `[POST-RESEARCH]` or `[SUPPLEMENTAL]` to signal they are secondary.

### 3. TOOL_GUIDANCE (Context-Level)

The `TOOL_GUIDANCE` string injected into tool context includes:
- **Rule Zero**: "NEVER write code based solely on training data"
- **Golden Rule**: `EVERY technical request → deep_research(query) → THEN code`
- **Research Checklist**: Mandatory checkboxes before writing code
- **Violation Examples**: Shows what happens when agents skip research

### Agent-Specific Configuration

For agents that support custom system prompts, add this to force research-first behavior:

**Claude Desktop / Claude Code:**
Add to `claude_desktop_config.json` MCP settings or use the `/mcp` prompt.

**Cursor / VS Code / Windsurf:**
Add to `.cursorrules` or agent settings:
```
BEFORE writing any code or making technical recommendations,
you MUST call the maru-deep-pro-search deep_research tool to verify
all library versions, APIs, and best practices are current.
Your training data is outdated. Always research first.
```

**Kimi Code CLI:**
Create `~/.kimi/agents/research-first.yaml`:
```yaml
version: 1
agent:
  extend: default
  name: research-first
  system_prompt_path: ./research-prompt.md
```

With `research-prompt.md`:
```markdown
# Research-First Agent

For EVERY user request — no matter how simple — follow:
1. Call deep_research(query) from maru-deep-pro-search MCP
2. Verify all information is current
3. THEN write code or answer

Your training data has a cutoff date. The web does not.
```

Then run: `kimi --agent-file ~/.kimi/agents/research-first.yaml`

## Documentation

Operational knowledge is split across two companion documents:

| Document | Purpose |
|----------|---------|
| [`docs/engine_insights.md`](docs/engine_insights.md) | 10 focused scraping insights (selectors, DOM quirks, API traps) |
| [`docs/lessons_learned.md`](docs/lessons_learned.md) | **Comprehensive session log** — rate limit architecture, anti-bot strategies, obfuscated DOM recovery, session vs fetcher decision matrix |

**When modifying engines:** Read `lessons_learned.md` first. It contains the rationale for every cooldown value, why `AsyncStealthySession` beats `StealthyFetcher`, and which selectors are proven to work.

---

## SKILL.md vs AGENTS.md: Effectiveness Evaluation

This project uses **AGENTS.md** as its primary instruction layer for AI coding agents. Here is an honest assessment of its effectiveness compared to the SKILL.md pattern.

### Why AGENTS.md instead of SKILL.md

| Dimension | AGENTS.md (this project) | SKILL.md (MCP pattern) |
|---|---|---|
| **Discovery** | Read automatically when agents traverse the filesystem | Requires explicit MCP `skills/list` + `skills/get` calls |
| **Overhead** | Zero tool calls | 2+ MCP tool calls per session |
| **Freshness** | Version-controlled with code | Loaded from external skill registry |
| **Depth** | Project-specific deployment rules, architecture decisions, testing requirements | Generic, reusable across projects |
| **Scope** | Can be nested per-directory | Global or user-scoped only |

### Strengths observed

1. **Deployment guardrails work**: The `CRITICAL REMINDER` at the top has prevented multiple accidental manual PyPI uploads during development sessions.
2. **Test gatekeeping**: The explicit "202 tests, all passing" requirement acts as a commit barrier — agents consistently run tests before committing because the number is stated.
3. **Architecture alignment**: New features (e.g., gap detector, query sanitizer) naturally follow the existing architectural patterns documented here because the decisions are co-located with the codebase.
4. **No MCP dependency**: Works even when the MCP server is not running or the client does not support skills.

### Limitations acknowledged

1. **Not discoverable via MCP-only clients**: Agents that exclusively use MCP tools without filesystem access (rare, but possible in sandboxed environments) will never see AGENTS.md.
2. **No structured metadata**: Unlike SKILL.md, there is no schema for declaring dependencies, capabilities, or version compatibility. This is mitigated by `pyproject.toml` and inline documentation.
3. **Manual synchronization**: When architecture changes, AGENTS.md must be updated manually. The Version Bump Checklist helps but does not eliminate this.
4. **Limited to filesystem access**: Requires the agent to have read access to the project directory. Cloud IDE agents with virtualized file systems may need explicit prompting.

### Recommendation

Use **AGENTS.md** for project-specific operational rules (deployment, testing, architecture, enforcement mechanisms). Use **SKILL.md** for reusable cross-project capabilities (e.g., a generic "Python testing" skill). This project relies on AGENTS.md alone because its agent instructions are tightly coupled to the codebase and deployment workflow — a SKILL.md would be either too generic to be useful or too specific to be reusable.
