# Agent Instructions for maru-search

> **CRITICAL REMINDER**: PyPI deployment is handled **automatically by GitHub Actions**. Do NOT attempt manual PyPI uploads via `twine`.

## Deployment Workflow

### PyPI Publishing (AUTOMATED)

The project uses **GitHub Actions** with **trusted publishing** to deploy to PyPI automatically:

- **Trigger**: Push a git tag starting with `v` (e.g., `v0.5.0`)
- **Workflow**: `.github/workflows/publish.yml`
- **Method**: Trusted publishing (no API tokens needed)

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
3. Publishes to PyPI with `uv publish --trusted-publishing always`
4. Package appears on https://pypi.org/project/maru-search/

### DO NOT

- ❌ Run `twine upload` manually
- ❌ Store PyPI API tokens locally
- ❌ Create `.pypirc` files
- ❌ Attempt direct uploads from local machine

### GitHub Pages Deployment

GitHub Pages is automatically deployed from the `docs/` directory on every push to `main`.

## Version Bump Checklist

Before creating a new release tag:

- [ ] Update `version` in `pyproject.toml`
- [ ] Update `CHANGELOG.md` with new version section
- [ ] Update version badge in `docs/index.html` (hero badge)
- [ ] Update test count in `docs/index.html` if changed
- [ ] Update test count in `README.md` if changed
- [ ] Run full test suite: `pytest tests/ -v` (all must pass)
- [ ] Commit all changes
- [ ] Push to `main`
- [ ] Create and push version tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
- [ ] Verify GitHub Actions workflow succeeds
- [ ] Verify PyPI page shows new version

## Project Structure Reminders

```
src/maru_search/
├── __init__.py            # Version info
├── server.py              # MCP server + prompts (8 tools)
├── tools.py               # 8 MCP tools + TOOL_GUIDANCE + TOOLS registry
├── config.py              # Runtime configuration
├── exceptions.py          # Structured exception hierarchy
├── engines/               # Search engine implementations + registry
│   ├── base.py            # SearchEngine ABC, SearchResult/PageContent
│   ├── registry.py        # SearchEngineRegistry (factory pattern)
│   ├── duckduckgo.py      # DuckDuckGoEngine (SERP + fetch)
│   ├── searxng.py         # SearXNGEngine (JSON API + 6-instance failover)
│   ├── bing.py            # BingEngine (HTML scrape)
│   ├── google.py          # GoogleEngine (CAPTCHA detection + fallback)
│   ├── naver.py           # NaverEngine (Korean search)
│   ├── qwant.py           # QwantEngine (European privacy)
│   └── startpage.py       # StartpageEngine (Google via privacy proxy)
├── extraction/            # Content extraction utilities
│   ├── code.py            # 21-language detection, API extraction
│   └── content.py         # truncate_for_llm, headings, token estimation
├── research/              # Deep research pipeline
│   ├── deep.py            # Deep research + answer synthesis + citations
│   ├── expander.py        # Query expansion (template-based)
│   └── ranker.py          # BM25 + metadata cross-engine ranking
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

**Current requirement**: 124 tests, all passing.

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

## Forcing Agents to Research Before Coding

The #1 problem with AI coding agents: they rely on stale training data instead of live web search. `maru-search` solves this at the MCP server level through three enforcement mechanisms:

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
Searches 7 engines live → BM25 ranks → crawls → synthesizes cited answer.
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
you MUST call the maru-search deep_research tool to verify
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
1. Call deep_research(query) from maru-search MCP
2. Verify all information is current
3. THEN write code or answer

Your training data has a cutoff date. The web does not.
```

Then run: `kimi --agent-file ~/.kimi/agents/research-first.yaml`
