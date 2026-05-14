# Agent Instructions — maru-deep-pro-search

> **CRITICAL**: PyPI deployment is **AUTOMATED** on git tag push. DO NOT use `twine`.

## Quick Start

```bash
uv sync && source .venv/bin/activate

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
- [ ] `pytest tests/ -q` passes (900+ tests)
- [ ] `__version__` synced with `pyproject.toml`
- [ ] Direct push to `main` is **PROHIBITED** — open a PR

---

## Code Style

- **ruff**: line length 100
- **Imports**: `from __future__ import annotations` at top
- **Types**: Full hints; `Any` only with `# type: ignore[no-any-return]`
- **Naming**: snake_case (functions), PascalCase (classes)
- **Docstrings**: Google style for public APIs

## Anti-Waste Policy (CTO Directive)

> **Coverage-only tests are BANNED.** If a test cannot plausibly catch a real bug, do not write it.

| Allowed | Banned |
|---------|--------|
| Tests that verify non-trivial logic, edge cases, or regression fixes | Tests that mock every dependency and assert `x == x` |
| Integration tests that expose real behavior changes | Boilerplate adapter tests whose only failure mode is the test itself |
| Tests for complex conditional branches (error handling, state machines) | Path getter tests that merely mirror the source code |
| Benchmark / performance regression tests | "23 tests for 100% coverage" where 20 are worthless |

**Rule of thumb**: Before writing a test, ask "If I intentionally break this logic, will this test fail?" If no → skip it. Use the time for architecture work instead.

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
uv run pytest tests/ -v        # All (900+)
uv run pytest tests/test_engines.py -v  # Specific
```

**Integration tests** (`test_tool_integration.py`) call real search engines. Flake is acceptable — it means we notice when engines break.

**Output format invariants** (do NOT break without updating tests):
- `deep_research`: `## Research:`, `_engines:`, `### Sources`, `#### [N] Title`, `_score:`
- `web_search`: `Search:`, numbered results `1. **Title** [N]`
- `fetch_page`: `EXTERNAL CONTENT`, `AGENT SECURITY PROTOCOL`
- `parallel_search`: `### Comparison Summary`, `| Query | Top Source | Type | Primary |`

---

## Things to Avoid (Gotchas)

| # | Trap | Fix |
|---|------|-----|
| 1 | `__version__` ≠ `pyproject.toml` | Verify BOTH files on every bump |
| 2 | PyPI re-upload same version | Must cut new version (0.11.2 → 0.11.3) |
| 3 | cubic push breaks lint | Run full validation after ANY cubic push |
| 4 | dependabot summary only | Read FULL advisory text before dismissing |
| 5 | `hasattr()` hides intent | Use explicit dataclass contracts |
| 6 | `str(cache.get(key))` | Converts `None` → `"None"`. Use `assert key is not None` |
| 7 | `\|\| true` in CI | Silently ignores failures. Remove it entirely |
| 8 | Dead code | Verify computed values are actually consumed |
| 9 | f-string without placeholders | ruff F541. Remove `f` prefix if no `{}` |
| 10 | YAML front matter indent | `description: >` requires indent on continuation lines |
| 11 | YAML colon in strings | Colons need quoting (`'...'`) in front matter |
| 12 | Invariant omission | Modifying output formats? Update BOTH code AND tests |
| 13 | Outdated dependabot PR | `@dependabot rebase` before merging after main changes |
| 14 | `gh pr create` body | Bash interprets backticks/pipes/dollars. Use `--body-file` |
| 15 | Not pulling main post-merge | `git pull` or stale files remain locally |
| 16 | Assuming PR is merged | Always `gh pr view N --json state` before acting |

---

## Release Workflow

```bash
# 1. Update version in BOTH pyproject.toml AND __init__.py
# 2. Update CHANGELOG.md + docs/index.html badge
# 3. Full validation → PR → cubic → merge
# 4. git checkout main && git pull
# 5. git tag vX.Y.Z && git push origin vX.Y.Z
# 6. gh run watch --workflow=publish.yml
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

Multi-engine vs single-engine (TREC-standard, 10 queries):
- Precision@5: **+86%** | NDCG@10: **+36%** | MRR: **+25%**
- Trade-off: ~2× response time

---

## Lessons Learned from Execution

Insights discovered by **running** the code, not by reading it.

### Agent Behavior Design

1. **Token efficiency IS enforcement** — Long docs get ignored. 1-line rules get followed. SKILL.md ~50% compression + 13 one-line imperatives.
2. **Imperative > descriptive** — "STOP and search immediately" works better than "When you encounter uncertainty, consider searching."
3. **Mid-task triggers are the real value** — Agents search once then code for 30min. Error-driven, refactor-driven, and 10-15min self-check triggers actually change behavior.

### mypy Strict Mode (57 → 0 errors)

4. **`cache_key` explicit cast** — `dict.get()` returns `str | None`. Never use `str(cache.get(key))` — converts `None` to `"None"`. Use `assert key is not None`.
5. **Loop variable shadowing** — Reusing variable names in nested loops breaks inference.
6. **`__new__` attribute access** — Dataclass `__new__` bypasses tracking. Requires `# type: ignore[attr-defined]`.
7. **`Exception` catch narrows too wide** — `except Exception as e:` gives `e: Exception`. Assert subclass before specific access.
8. **Session redefinition** — Same variable in `if`/`else` with different types needs explicit first annotation.

### CI & Automation

9. **`\|\| true` silently ignores failures** — Found in `test.yml` and `lint.yml`. Removes all signal while wasting time.
10. **`gh pr create` body with backticks/pipes/dollars** — Bash interprets as command substitution. Always `--body-file`.
11. **cubic reviews stale commits** — Trust check status, not comment text. Comments may reflect older commits.
12. **pytest count changes** — When tests decrease, verify it's expected (e.g., removed feature).
13. **dependabot PR outdated** — Main changes? `@dependabot rebase` before merging. Otherwise lint/test fails on stale code.

### Packaging & Distribution

14. **Root-level files NOT pip-installed** — Only package directory files installed. `skills/` must live in `src/maru_deep_pro_search/skills/` with `[tool.setuptools.package-data]`.
15. **YAML front matter traps** — `description: >` requires indent. Colons need quoting.
16. **f-string without placeholders** — ruff F541. Remove `f` if no `{}`.

### Benchmark & Quality

17. **DuckDuckGo circuit breaker storm** — Back-to-back modes without `asyncio.sleep(5)` opens breaker.
18. **Single-engine can win** — `deep_research` does NOT universally dominate. On "httpx async" Bing single matched multi-engine.
19. **Ground truth breadth** — Narrow patterns (only `nvd.nist.gov`) penalize legitimate sources (GitHub Advisory, Snyk).

---

## Architecture Decisions

1. **100% FREE** — No paid APIs ever.
2. **Engine registry** — Multi-engine failover via `SearchEngineRegistry`.
3. **BM25 + metadata** — Perplexity-level quality, local computation.
4. **Citation-native** — `[1]`, `[2]` IDs without external services.
5. **Research-first** — MCP prompts + `TOOL_GUIDANCE` force search before coding.
6. **Prompt injection defense** — Zero-width chars removed, chat tokens neutralized.
7. **Three-layer rate limiting** — Semaphore(3) + cooldowns + token bucket.
8. **Session-reuse stealth** — `AsyncStealthySession` for Google/Startpage.
9. **MCP tools provide DATA** — Agent's LLM decides synthesis.
