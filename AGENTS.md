# Agent Instructions — maru-deep-pro-search

> **CRITICAL**: PyPI deployment is **AUTOMATED** on git tag push. DO NOT use `twine`.

## Quick Start

```bash
uv sync
source .venv/bin/activate

# Single-file (fast feedback)
uv run ruff check src/maru_deep_pro_search/<file>.py
uv run mypy src/maru_deep_pro_search/<file>.py

# Full validation
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest tests/ -q
```

**Definition of Done**
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `mypy src/` passes (0 errors)
- [ ] `pytest tests/ -q` passes (273 tests)
- [ ] `__version__` synced with `pyproject.toml`
- [ ] Direct push to `main` is **PROHIBITED** — open a PR

---

## Code Style

- **ruff**: line length 100
- **Imports**: `from __future__ import annotations` at top
- **Types**: Full hints; `Any` only with `# type: ignore[no-any-return]`
- **Naming**: snake_case (functions), PascalCase (classes)
- **Docstrings**: Google style for public APIs

### Inheritance Safety (MANDATORY)

**ALL subclasses overriding `__init__` MUST call `super().__init__()` as the FIRST statement.**

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
```

---

## Testing

```bash
# All tests (273 total)
uv run pytest tests/ -v

# Specific test
uv run pytest tests/test_engines.py -v
```

**Integration tests** (`test_tool_integration.py`) call real search engines. They may flake if engines are down — this is **acceptable**.

**Output format invariants** (do NOT break without updating tests):
- `deep_research`: `## Research:`, `_engines:`, `### Sources`, `#### [N] Title`, `_score:`
- `web_search`: `Search:`, numbered results `1. **Title** [N]`
- `fetch_page`: `EXTERNAL CONTENT`, `AGENT SECURITY PROTOCOL`
- `parallel_search`: `### Comparison Summary`, `| Query | Top Source | Type | Primary |`

---

## Things to Avoid (Gotchas)

| Trap | Why | Fix |
|------|-----|-----|
| `__version__` ≠ `pyproject.toml` | Runtime reports wrong version | Verify BOTH files on every bump |
| PyPI re-upload same version | Wheel is immutable | Must cut new version (0.11.2 → 0.11.3) |
| cubic push breaks lint | cubic does NOT run `ruff check` before push | Always run full validation after cubic push |
| dependabot summary only | Summary understates required version | Read FULL advisory text before dismissing |
| `hasattr()` hides intent | Returns `False` silently after refactors | Use explicit dataclass contracts |
| `str(cache.get(key))` | Converts `None` to `"None"`, masks bugs | Use `assert key is not None` |
| `\|\| true` in CI | Silently ignores failures, wastes time | Remove entirely; let CI actually fail |
| Dead code | Computed but never consumed | Always verify values are used |
| f-string without placeholders | ruff F541 lint error | Remove `f` prefix if no `{}` |

---

## Release Workflow

```bash
# 1. Update version in BOTH pyproject.toml AND __init__.py
# 2. Update CHANGELOG.md + docs/index.html badge
# 3. Full validation
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest tests/ -v
# 4. PR → cubic review → merge
# 5. git checkout main && git pull
# 6. git tag vX.Y.Z && git push origin vX.Y.Z
# 7. gh run watch --workflow=publish.yml
```

---

## Code Review & Merge Workflow

```
1. git checkout -b feat/description
2. 작업 + 커밋
3. git push -u origin feat/description
4. gh pr create --title "feat: description" --body-file /tmp/pr.md
5. cubic AI 리뷰 → 피드백 반영 → push
6. 머지 조건: CI 전체 통과 + cubic pass
```

**After ANY cubic push to PR branch:**
```bash
git pull origin <branch>
uv run ruff check src/ && uv run ruff format --check src/ && uv run mypy src/
uv run pytest tests/ -q
```

---

## Benchmarks

```bash
uv run python benchmark/search_quality_benchmark.py
```

| Metric | web_search (Bing) | deep_research (multi) | Delta |
|--------|-------------------|----------------------|-------|
| Precision@5 | 0.140 | **0.260** | +86% |
| NDCG@10 | 0.488 | **0.668** | +36% |
| MRR | 0.483 | **0.603** | +25% |

Trade-off: ~2× response time.

---

## Lessons Learned from Execution

These insights were discovered by **running** the code, not by reading it.

### Agent Behavior Design

1. **Token efficiency IS enforcement** — Long docs get ignored. 1-line rules get followed. SKILL.md was compressed ~50% and protocol rewritten into 13 one-line imperatives.
2. **Imperative > descriptive** — "STOP and search immediately" works better than "When you encounter uncertainty, consider searching."
3. **Mid-task search triggers are the real value** — Agents search once at start then code for 30min. Error-driven, refactor-driven, and 10-15min self-check triggers are what actually change behavior.

### mypy Strict Mode (57 → 0 errors)

4. **`cache_key` explicit cast** — `dict.get()` returns `str | None`. Never use `str(cache.get(key))` — it converts `None` to `"None"`. Use `assert key is not None`.
5. **Loop variable shadowing** — Reusing the same variable name in nested loops breaks mypy inference.
6. **`__new__` attribute access** — Dataclass `__new__` bypasses mypy tracking. Requires `# type: ignore[attr-defined]` or typed protocol.
7. **`Exception` catch narrows too wide** — `except Exception as e:` gives `e: Exception`. Assert subclass before accessing specific attributes.
8. **Session redefinition across branches** — Same variable in `if`/`else` with different types needs explicit annotation on first assignment.

### CI & Automation

9. **`\|\| true` silently ignores failures** — Found in both `test.yml` and `lint.yml`. Removes all signal while wasting runner time.
10. **`gh pr create` body with backticks/pipes/dollars** — Bash interprets them as command substitution. Always use `--body-file`.
11. **cubic reviews stale commits** — Trust the check status (`cubic · AI code reviewer: pass`), not just the comment text. Comments may reflect an older commit.
12. **pytest count changes must be intentional** — When tests decrease, verify it's expected (e.g., removed feature).

### Packaging & Distribution

13. **Root-level files are NOT pip-installed** — Only files under package directories are installed. `skills/` must live inside `src/maru_deep_pro_search/skills/` with `[tool.setuptools.package-data]`.
14. **YAML front matter traps** — `description: >` requires indent on continuation lines. Colons in strings need quoting (`'...'`).
15. **f-string without placeholders** — ruff F541. Remove `f` prefix if no `{}` inside.

### Benchmark & Quality

16. **DuckDuckGo circuit breaker storm** — Back-to-back benchmark modes without `asyncio.sleep(5)` opens the breaker. Always delay between modes.
17. **Single-engine can win individual queries** — `deep_research` does NOT universally dominate. On "httpx async client tutorial" Bing single matched multi-engine. Average matters.
18. **Ground truth patterns must be broad** — Narrow patterns (only `nvd.nist.gov` for CVE) penalize legitimate sources (GitHub Advisory, Snyk).

---

## Architecture Decisions (one-liners)

1. **100% FREE** — No paid APIs ever.
2. **Engine registry** — Multi-engine failover via `SearchEngineRegistry`.
3. **BM25 + metadata ranking** — Perplexity-level quality, local computation only.
4. **Citation-native** — `[1]`, `[2]` IDs without external services.
5. **Research-first enforcement** — MCP prompts + `TOOL_GUIDANCE` force agents to search before coding.
6. **Prompt injection defense** — Zero-width chars removed, chat tokens neutralized.
7. **Three-layer rate limiting** — Semaphore(3) + per-engine cooldowns + token bucket.
8. **Session-reuse stealth** — `AsyncStealthySession` for Google/Startpage.
9. **MCP tools provide DATA, not INTELLIGENCE** — Agent's LLM decides synthesis.
