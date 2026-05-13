# Agent Instructions — maru-deep-pro-search

> **CRITICAL**: PyPI deployment is **AUTOMATED** by GitHub Actions on git tag push. DO NOT run `twine upload` manually.

## Quick Start

```bash
# Setup
uv sync
source .venv/bin/activate

# Single-file checks (fast feedback)
uv run ruff check src/maru_deep_pro_search/<file>.py
uv run ruff format --check src/maru_deep_pro_search/<file>.py
uv run mypy src/maru_deep_pro_search/<file>.py

# Full validation
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest tests/ -q

# Run MCP server locally
uv run python -m maru_deep_pro_search.server
```

**Definition of Done** — Before declaring a task complete, verify:
- [ ] `ruff check .` passes with zero errors
- [ ] `ruff format --check .` passes
- [ ] `mypy src/maru_deep_pro_search` passes (0 errors)
- [ ] `pytest tests/ -q` passes (273 tests)
- [ ] `__version__` in `__init__.py` matches `pyproject.toml` if version changed
- [ ] Direct push to `main` is PROHIBITED — open a PR

---

## Tech Stack

- **Python**: 3.12
- **Package Manager**: uv (replaces pip/poetry)
- **Formatter/Linter**: ruff (line length 100)
- **Type Checker**: mypy (strict)
- **Test**: pytest + pytest-asyncio + pytest-cov
- **Search Scrapers**: scrapling (DuckDuckGo, Google, Bing, Baidu, Naver, Yahoo, Ecosia, Startpage, Bing)
- **API**: MCP (Model Context Protocol) server with 10 tools
- **CI**: GitHub Actions (lint, test, CodeQL, PyPI publish)

---

## Setup Commands

### File-scoped (preferred — fast feedback)

```bash
# Type-check a single file
uv run mypy src/maru_deep_pro_search/<file>.py

# Lint a single file
uv run ruff check src/maru_deep_pro_search/<file>.py
uv run ruff format --check src/maru_deep_pro_search/<file>.py

# Run one test file
uv run pytest tests/test_<name>.py -v
```

### Full suite (only when explicitly requested)

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest tests/ -v
```

---

## Code Style

- **Formatting**: ruff, line length 100
- **Imports**: `from __future__ import annotations` at top; sorted by `ruff check --fix`
- **Types**: Full type hints required; `Any` only with `# type: ignore[no-any-return]` if runtime validation is impossible
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Docstrings**: Google style for public APIs

### Inheritance Safety (MANDATORY)

**ALL subclasses overriding `__init__` MUST call `super().__init__()` as the FIRST statement.**

The `SearchEngine` base class initializes `self._circuit_breaker` and `self._last_request_time` in `__init__`. Skipping `super().__init__()` causes silent failures that only explode at runtime when `search()` is called:

```python
# ❌ WRONG
class XEngine(SearchEngine):
    def __init__(self):
        self.x = 1  # _circuit_breaker missing!

# ✅ CORRECT
class XEngine(SearchEngine):
    def __init__(self):
        super().__init__()  # FIRST line
        self.x = 1
```

Every new `SearchEngine` subclass MUST include an instantiation test:
```python
engine = SomeNewEngine()
assert hasattr(engine, '_circuit_breaker')
assert hasattr(engine, '_last_request_time')
```

---

## Testing

```bash
# All tests (273 total)
uv run pytest tests/ -v

# Specific test
uv run pytest tests/test_engines.py -v
```

**Integration tests** (`test_tool_integration.py`) call real search engines. They may flake if engines are down — this is **acceptable**; it means we notice when engines break.

**Output format invariants** (do NOT break without updating tests):
- `deep_research`: `## Research:`, `_engines:`, `### Sources`, `#### [N] Title`, `_score:`
- `web_search`: `Search:`, numbered results `1. **Title** [N]`, indented URLs
- `fetch_page`: `EXTERNAL CONTENT`, `AGENT SECURITY PROTOCOL`
- `parallel_search`: `### Comparison Summary`, `| Query | Top Source | Type | Primary |`

---

## Project Structure

```
src/maru_deep_pro_search/
├── server.py          # MCP server + 10 tools + prompts
├── tools.py           # MCP tool implementations + TOOL_GUIDANCE
├── config.py          # Runtime configuration
├── exceptions.py      # Structured exception hierarchy
├── engines/           # 9 search engines + registry
│   ├── base.py        # SearchEngine ABC + circuit breaker wrapping
│   ├── registry.py    # SearchEngineRegistry (factory)
│   └── duckduckgo.py  # Default engine (DuckDuckGo SSR)
├── research/          # Deep research pipeline
│   ├── deep.py        # Search-only deep research (319 lines)
│   └── semantic_ranker.py  # Optional sentence-transformers
├── harness/           # KnowledgeStore (SQLite) + workflow engine
└── utils/             # retry, url, query sanitize
```

---

## Architecture Decisions

1. **100% FREE — No paid APIs ever** — All search, ranking, extraction work with zero API keys. Only direct scraping and local computation.
2. **Engine registry pattern** — `SearchEngineRegistry` enables multi-engine failover (all free scrapers).
3. **BM25 + metadata ranking** — Perplexity-level quality using only local computation.
4. **Citation-native output** — All results include `[1]`, `[2]` citation IDs without external services.
5. **Research-first enforcement** — MCP prompts, tool descriptions, and `TOOL_GUIDANCE` FORCE agents to research before coding.
6. **Prompt injection defense** — Fetched content is sanitized (zero-width chars removed, chat tokens neutralized).
7. **Three-layer rate limiting** — `asyncio.Semaphore(3)` + per-engine cooldowns + global token bucket.
8. **Session-reuse stealth** — Google/Startpage use `AsyncStealthySession` (browser reuse) instead of new browser per call.
9. **MCP tools provide DATA, not INTELLIGENCE** — `deep_research` returns ranked URLs + metadata only. The agent's LLM decides which sources to read and how to synthesize.

---

## Security

- **Secrets**: Use environment variables; never hardcode credentials
- **urllib3**: Pinned to `>=2.7.0` (CVE-2026-44431)
- **Fetched content**: Always sanitized before LLM injection
- **GitGuardian**: Runs on every PR to catch leaked secrets

---

## Things to Avoid (Gotchas)

### ❌ `__version__` is NOT auto-synced with `pyproject.toml`
`src/maru_deep_pro_search/__init__.py` contains hard-coded `__version__`. PyPI can show `0.11.3` while runtime reports `0.9.2`. **Always verify both files on version bumps.**

### ❌ PyPI does NOT allow re-uploading the same version
Once a tag is pushed, the wheel is immutable. If a bug is discovered post-release, you MUST cut a new version (e.g., `0.11.2` → `0.11.3`).

### ❌ cubic's AI commits can still break lint
cubic pushes commits but does NOT run `ruff check` first. After ANY cubic push, run lint locally or wait for CI and push a follow-up fix.

### ❌ dependabot dismiss requires reading the FULL advisory
The summary often understates the required version. CVE-2026-44431 summary suggested `>=2.2.2`; the full text required `>=2.7.0`.

### ❌ `hasattr()` hides intent
Prefer explicit dataclass contracts. `hasattr(src, "markdown")` silently returns `False` after refactors instead of failing loud.

### ❌ Dead code is worse than no code
Always verify computed values are actually consumed. `urls_to_prioritize()` in `deep.py` was computed but never used.

---

## Release Workflow

```bash
# 1. Update version in BOTH files
#    pyproject.toml: version = "X.Y.Z"
#    src/maru_deep_pro_search/__init__.py: __version__ = "X.Y.Z"

# 2. Update CHANGELOG.md with new version section

# 3. Update docs/index.html hero badge

# 4. Run full validation
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest tests/ -v

# 5. Commit on main (via PR)
git checkout -b release/vX.Y.Z
git add -A && git commit -m "release: vX.Y.Z"
# Open PR → cubic AI review → merge

# 6. Tag triggers PyPI auto-deploy
git checkout main && git pull
git tag vX.Y.Z && git push origin vX.Y.Z

# 7. Verify
gh run watch --workflow=publish.yml
python -c "import maru_deep_pro_search; print(maru_deep_pro_search.__version__)"
```

---

## Code Review & Merge Workflow

### Required: PR-based development

**Direct pushes to `main` are PROHIBITED.** All changes must go through a Pull Request so cubic AI review can run.

```
1. git checkout -b feat/description
2. 작업 + 커밋
3. (선택) cubic review --base main   # 로컬 사전 검증
4. git push -u origin feat/description
5. gh pr create --title "feat: description" --body "..."
6. cubic AI가 PR 자동 리뷰
7. 피드백 반영 후 push
8. 머지 조건: CI 전체 통과 + cubic resolved + 1 approving review
```

### Post-cubic-push checklist

After ANY cubic AI push to a PR branch:
```bash
git pull origin <branch>
uv run ruff check src/ && uv run ruff format --check src/ && uv run mypy src/
uv run pytest tests/ -q
```

---

## Permissions

### Allowed without prompting
- Read/list files
- Single-file lint, type check, format
- Single test file run
- Edit existing code

### Ask first
- `uv add` new dependencies
- `git push` to remote
- File deletion
- Full test suite or E2E runs
- Version tag creation

---

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/engine_insights.md` | 10 scraping insights (selectors, DOM quirks) |
| `docs/lessons_learned.md` | Rate limit architecture, anti-bot strategies, obfuscated DOM recovery |
| `AGENT_COMPATIBILITY.md` | Per-agent setup (Claude, Cursor, Kimi, etc.) |

**When modifying engines**: Read `docs/lessons_learned.md` first. It contains the rationale for every cooldown value and proven selector.

---

## Skills (SKILL.md)

Modular skills for MCP-compatible agents. Each skill provides domain-specific guidance:

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `skills/deep-research/SKILL.md` | How to use `deep_research` effectively | Before technical decisions |
| `skills/web-search/SKILL.md` | How to use `web_search` + engine selection | Quick lookups |
| `skills/fetch-page/SKILL.md` | Safe content fetching + risk levels | Reading external sources |
| `skills/parallel-search/SKILL.md` | Comparative multi-query search | Technology comparisons |

Load skills via `skills-mcp` or include directly in agent context.

---

## Benchmarks

Search quality is measured against TREC-standard IR metrics:

```bash
# Run search quality benchmark (10 queries, web_search vs deep_research)
uv run python benchmark/search_quality_benchmark.py
```

Metrics: Precision@K, Recall@K, NDCG@K, MRR, response time.

**Latest result** (10 queries, Bing single vs multi-engine cross-ranking):

| Metric | web_search | deep_research | Delta |
|--------|-----------|---------------|-------|
| Precision@5 | 0.140 | **0.260** | **+86%** |
| NDCG@10 | 0.488 | **0.668** | **+36%** |
| MRR | 0.483 | **0.603** | **+25%** |

Multi-engine cross-ranking outperforms single-engine on all relevance metrics.
Trade-off: ~2× response time (multi-engine search overhead).

---

## Lessons Learned from Execution

These insights were discovered by **running** the code, not by reading it. They capture behavior that is invisible in static analysis.

### Benchmark Execution

1. **DuckDuckGo circuit breaker storm** — Running benchmark modes back-to-back without delay causes the circuit breaker to open on the second mode. Always insert `await asyncio.sleep(5)` between `web_search` and `deep_research` benchmark runs.
2. **Single-engine can win individual queries** — `deep_research` does NOT universally dominate. On "httpx async client tutorial" and "pytest asyncio fixture", Bing single-engine matched or beat multi-engine. Average matters, not every query.
3. **Ground truth patterns must be broad** — Narrow patterns (e.g., only `nvd.nist.gov` for CVE queries) penalize legitimate security sources (GitHub Advisory, Snyk). Binary relevance scoring is sensitive to pattern breadth.
4. **Query type strongly predicts engine quality** — Technical documentation queries (FastAPI, Python docs) benefit massively from multi-engine. Comparison queries ("vs") and CVE queries show smaller or negative deltas.

### mypy Strict Mode (57 → 0 errors)

1. **`cache_key` requires explicit cast** — `dict.get()` returns `str | None`; mypy cannot narrow through `if key is not None`. Cast: `str(cache.get(key))` or assert.
2. **Loop variable shadowing breaks inference** — Reusing the same variable name in nested loops causes mypy to infer the outer variable's type from the inner loop's assignment.
3. **`__new__` attribute access is invisible** — Dataclass `__new__` implementations bypass mypy's attribute tracking. Accessing attributes set in `__new__` requires `# type: ignore[attr-defined]` or a typed protocol.
4. **`Exception` catch narrows too wide** — `except Exception as e:` gives `e: Exception`. If you later access subclass-specific attributes, assert the type: `assert isinstance(e, MyError)`.
5. **Session redefinition across branches** — Assigning `session = ...` in both `if` and `else` branches with different types requires explicit annotation on the first assignment.

### cubic AI Review Behavior

1. **cubic pushes with `--force-with-lease`** — It does NOT open a separate commit; it amends and force-pushes to the PR branch. Always `git pull --rebase` before adding your own commits.
2. **cubic does NOT run lint before push** — After cubic pushes, always run the full validation suite locally. The PR CI will catch it, but local verification is faster.
3. **cubic focuses on correctness over style** — It catches logic bugs and security issues but rarely comments on naming or docstring quality. Those remain the human's responsibility.

### Multi-Engine Trade-offs

| Dimension | Single-Engine (Bing) | Multi-Engine (deep_research) |
|-----------|---------------------|------------------------------|
| Precision@5 | 0.140 | **0.260** (+86%) |
| MRR | 0.483 | **0.603** (+25%) |
| Response Time | ~2s | ~4–6s |
| Coverage | 1 engine | 3+ engines (dedup by class) |
| Best For | Simple homepage lookups | Technical docs, cross-source verification |

**Rule of thumb**: If the query is "go to X's official docs", single-engine is sufficient. If the query is "how does X work" or "X vs Y", always use multi-engine.
