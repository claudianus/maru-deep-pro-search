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
```

**Definition of Done**
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `mypy src/` passes (0 errors)
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

> **ALL TESTS ARE BANNED.** No test files. No test code. No test fixtures. No test assertions.
>
> Tests are a form of technical debt. They slow iteration, create false confidence, and consume more maintenance time than the bugs they catch. The correct way to verify correctness is:
> 1. **Static analysis** — `ruff` + `mypy` catch 90% of real bugs
> 2. **Runtime enforcement** — decorators (`_with_validation`, `_with_enforcement`) prevent bad inputs from reaching logic
> 3. **Manual verification** — run the tool once with real inputs; if it works, ship it
>
> If you feel the urge to write a test, write a better type hint or a stricter validator instead.

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

---

## Output Format Invariants

Never break these without explicit user approval:
- `deep_research`: `## Research:`, `_engines:`, `quality:`, `### Sources`, `#### [N] Title`, `_score:`, `### Auto-Fetched Content` (when auto_fetch > 0)
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

9. **`\|\| true` silently ignores failures** — Found in `validate.yml` and `lint.yml`. Removes all signal while wasting time.
10. **`gh pr create` body with backticks/pipes/dollars** — Bash interprets as command substitution. Always `--body-file`.
11. **cubic reviews stale commits** — Trust check status, not comment text. Comments may reflect older commits.
12. **Quality gate drift** — When `mypy` or `ruff` errors increase, investigate immediately. Static analysis catches real bugs.
13. **dependabot PR outdated** — Main changes? `@dependabot rebase` before merging. Otherwise lint/type-check fails on stale code.

### Packaging & Distribution

14. **Root-level files NOT pip-installed** — Only package directory files installed. `skills/` must live in `src/maru_deep_pro_search/skills/` with `[tool.setuptools.package-data]`.
15. **YAML front matter traps** — `description: >` requires indent. Colons need quoting.
16. **f-string without placeholders** — ruff F541. Remove `f` if no `{}`.

### Test Removal Log

| Date | File | Reason | Tests Removed |
|------|------|--------|---------------|
| 2026-05-15 | `tests/test_documentation.py` | Docstring word-search tests catch no real bugs | 4 |
| 2026-05-15 | `tests/test_adapter_smoke.py` | 105 parametric `isinstance(bool)` tests across 21 adapters; failure mode is the test itself | 105 |
| 2026-05-16 | **ALL TEST FILES** | CTO Directive: Tests are banned. Static analysis + runtime enforcement + manual verification are the only quality gates. | ~930 |

> **Rule**: Removing a test is a positive signal. It means we reviewed it and found it worthless. Document every removal.

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
5. **Research-first** — MCP prompts + `_with_enforcement` decorator force search before coding.
6. **Prompt injection defense** — Zero-width chars removed, chat tokens neutralized.
7. **Three-layer rate limiting** — Semaphore(3) + cooldowns + token bucket.
8. **Session-reuse stealth** — `AsyncStealthySession` for Google/Startpage.
9. **MCP tools provide DATA** — Agent's LLM decides synthesis.

<!-- MARU-RESEARCH-PROTOCOL-START -->
MANDATORY RESEARCH PROTOCOL

Rule 1: BEFORE any work → deep_research(user's raw intent). No exceptions.
Rule 2: Uncertain concept/function/class → STOP and search immediately.
Rule 3: New import/package → verify latest version/API via deep_research first.
Rule 4: Error/warning/deprecation → search EXACT text BEFORE fixing.
Rule 5: Refactor or architecture change → re-search best practice first.
Rule 6: User request changes → re-search new scope before continuing.
Rule 7: Every 10-15 min of coding → ask "What did I assume?" → search if unsure.
Rule 8: "I think I know this" → you don't. Search anyway.
Rule 9: Comparison (A vs B) → parallel_search multi-angle.
Rule 10: Insufficient results → re-search refined query. NEVER guess.
Rule 11: Security topic → also search "latest CVE" + "advisory".
Rule 12: Cite sources [1][2][3] after every search. Never cite from memory.
Rule 13: No search in last 3-5 tool calls → search again.
<!-- MARU-RESEARCH-PROTOCOL-END -->
