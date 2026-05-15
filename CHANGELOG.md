# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.13.0] - 2026-05-15

### Added
- **Research Drift Guard** — Tracks manifest fingerprints (`pyproject.toml`, lockfiles, etc.) and error signatures between `deep_research` calls; appends drift warnings to tool output with suggested micro-queries (no local LLM).
- **`drift_status` MCP tool** — Read-only drift report without web search (research-exempt).
- **`maru-deep-pro-search-knowledge`** CLI — `export` / `import` portable JSON bundles for team knowledge sharing (optional, bounded to 500 entries).

### Changed
- **`session_state`** includes drift summary when manifests changed.
- **`.maru/receipts/`** added to default harness `.gitignore` template.

## [0.12.0] - 2026-05-15

### Added
- **Research Receipt** — `deep_research` writes `~/.maru/receipts/RSCH-*.md` + JSON (citations, planned reads, excerpt). Auto-prune (~48 files, 14-day TTL) to limit disk use.
- **Fetch Planner (metadata-only)** — `### Recommended Reads` section ranks top 3 URLs via BM25 metadata + intent heuristics (security/docs/compare). No local LLM; host calls `fetch_page` / `fetch_bulk`.
- **`auto_fetch`** uses planned-read IDs when set (max 3, opt-in only).

### Changed
- **`research_id`** generated once in `deep_research` output; session enforcer reuses ID from tool text (no duplicate IDs).

## [0.11.3] - 2026-05-13

### Security
- **urllib3>=2.7.0** — Bump from >=2.2.2 to >=2.7.0 to fully address CVE-2026-44431 (sensitive headers in proxied redirects).

## [0.11.2] - 2026-05-13

### Security
- **urllib3>=2.2.2** — Explicitly pin urllib3 to patched version addressing 2 high-severity CVEs (sensitive header forwarding & decompression bomb bypass).

### Fixed
- **mypy type errors** — Resolved 57→0 errors across 16 files. No `# type: ignore[no-any-return]` without runtime validation.
- **cubic AI review workflow** — AGENTS.md now enforces PR-based development with cubic AI review as mandatory merge gate.

## [0.11.1] - 2026-05-13

### Added
- **`research` CLI subcommand** — `python -m maru_deep_pro_search.server research "query" --output report.md` for headless deep research from command line. Supports `--engine`, `--max-sources`, and `--no-expand` flags.
- **GitHub Actions workflow overhaul** — `maru-deep-pro-search workflow` now generates a production-ready workflow with:
  - pip caching via `actions/setup-python@v5`
  - Auto-posts research summary as PR/Issue comment via `gh CLI`
  - Supports `MARUBOT_TOKEN` secret for custom bot identity
  - Installs from current branch instead of PyPI (fallback)
  - Explicit `permissions` block for security

### Fixed
- **`workflow_cmd.py` SyntaxWarning** — Removed invalid backtick escape sequences in generated workflow template.
- **`.gitignore` hygiene** — Added `*.png` and `.playwright-mcp/` to prevent screenshot artifacts from being committed.

## [0.11.0] - 2026-05-13

### Changed (BREAKING ARCHITECTURE)
- **`deep_research` is now search-only** — Content fetching and answer synthesis are delegated to the agent's LLM. The agent receives ranked URLs with rich metadata (authority badges, cross-engine confirmation, source type) and decides which sources to read via `fetch_page` / `fetch_bulk`.
- **Removed from `deep_research`**: `_fetch_pages`, `_probe_network`, `_filter_slow_domains`, `_allocate_tokens`, `_extractive_summarize`, `_synthesize_answer`, recency gate, `follow_links`, knowledge-store persistence of full content.
- **Simplified `CitedSource`**: Removed `content`, `markdown`, `fetch_ms`, `code_languages`, `github_meta`, and other fetch-dependent fields.
- **`deep_research` signature simplified**: Removed `follow_links`, `max_tokens_per_source`, `max_total_tokens`, `summarize` parameters.
- **`format_for_llm()` redesigned**: Outputs URL list + snippet + metadata badges only. No more embedded full markdown per source. Typical output: ~1,500 chars (was 10,000+).
- **Response time**: 2–3s average (was 10–18s) — 70% faster.
- **Code size**: `deep.py` reduced from 1,194 to 319 lines (-73%).

### Fixed
- **`parallel_search` comparison_mode**: Empty titles in comparison table now show domain fallback instead of "(no title)". Individual search failures are handled gracefully instead of crashing the entire operation.
- **`_score_metadata` in ranker.py**: Replaced fragile `url.split('/')[2]` with `get_domain()` utility.
- **Expander templates**: Removed "GitHub Octoverse" and "Stack Overflow survey" templates that caused irrelevant `github.com` matches for every query.

### Added
- **18 integration tests** (`test_tool_integration.py`) that call real tools and verify output format — catches regressions in actual MCP output.

## [0.10.0] - 2026-05-13

### Added
- **Citation-Grade Source Quality Overhaul** — 7 prioritized improvements from production feedback
  1. **Canonical URL Accuracy**: `resolve_redirect()` now handles Google (`/url?url=`), DuckDuckGo (`r.duckduckgo.com`), Bing (`/ck/a`), Yahoo (`/RU=`), Baidu, and generic `?redirect=` / `?target=` patterns. `resolve_canonical_url()` provides a second normalization pass that strips tracking params and resolves redirectors.
  2. **Stable Citation IDs**: `deep_research` now renumbers sources sequentially after token allocation, eliminating gaps caused by dropped/blocked sources. `parallel_search` gains `comparison_mode=True` with global renumbering across all queries.
  3. **Primary Source Filter**: New `primary_sources_only` parameter on `deep_research` and `answer`. Filters out blogs/aggregators and keeps only official docs, GitHub repos, package registries, academic papers, and Stack Overflow.
  4. **GitHub Repo Metadata**: GitHub URLs automatically extract ⭐ stars, primary language, license, last push date, topics, and description into a structured `_GitHub: ..._` line.
  5. **Separated Freshness Info**: Sources now display `published: YYYY-MM-DD | updated: YYYY-MM-DD | age: Nd` instead of a single ambiguous freshness badge.
  6. **Explicit Source Type Classification**: Every result is tagged with `[OFFICIAL-DOCS]`, `[GITHUB-REPO]`, `[BLOG-REVIEW]`, `[TUTORIAL]`, `[ACADEMIC-PAPER]`, `[FORUM]`, `[PACKAGE-REGISTRY]`, `[NEWS]`, or `[UNKNOWN]`.
  7. **Comparison Mode for `parallel_search`**: When `comparison_mode=True`, results are merged into a summary table (`| Query | Top Source | Type | Primary |`) with globally renumbered citations.
- **Source Type Auto-Classification**: `guess_source_type_and_primary()` in `engines/base.py` + `classify_source_type()` / `is_primary_source()` in `utils/url.py` provide consistent classification across all 8 search engines.
- **Self-Update System** (`v0.10.0` add-on):
  - `maru-deep-pro-search update` — One-command self update (auto-detects `uv`, `pipx`, `pip`)
  - `maru-deep-pro-search update --check` — Dry-run version check only
  - `maru-deep-pro-search update --force` — Skip 24h cooldown
  - Background update check on MCP server startup (logs warning if newer version exists)
  - Cooldown stored in `~/.cache/maru-deep-pro-search/last_update_check`
  - Disabled via `MARU_SKIP_UPDATE_CHECK=1` or `MARU_UPDATE_CHECK_INTERVAL_HOURS`
- **49 new tests** covering URL canonicalization, source type classification, citation renumbering, primary source filtering, and updater logic.

### Changed
- `SearchResult` and `PageContent` now carry `source_type: SourceType` and `is_primary: bool` fields.
- `CitedSource` extended with `source_type`, `is_primary`, `github_meta`, `last_updated`, `crawled_at`.
- `format_for_llm()` output reorganized: source type badges appear before freshness, GitHub metadata gets its own line, `[PRIMARY]` badge highlights authoritative sources.

## [0.9.3] - 2026-05-13

### Added
- **3-Layer Rate Limit Architecture**: Prevents 429 storms on Google/Baidu under heavy load
  - `asyncio.Semaphore(3)`: Global concurrent search cap in `deep_research` and tools
  - `EngineRateLimiter`: Per-engine cooldowns auto-wrapped via `SearchEngine.__init_subclass__`
    - Google/Startpage: 3.0s, Baidu: 2.0s, Bing/Yahoo/Ecosia/Naver: 1.5s, DuckDuckGo: 1.0s
  - `TokenBucket` (optional): Global QPS throttling in `utils/rate_limiter.py`
- **Engine Reliability Overhaul**: Comprehensive scraping resilience improvements
  - **Naver**: Obfuscated DOM recovery (`sds-comps-*`, `fender-ui_*` bypassed via `.fds-web-doc-root` + `a[nocr="1"]`). Reliability 0.25→0.60, tier 3→2
  - **Baidu**: Noise filtering (`result-op` class exclusion for AI/ads). Added `ubs.baidu.com`, `recommend_list.baidu.com` to global skip lists
  - **Bing**: Locale pinning (`setmkt=en-US&setlang=en`) prevents geo-localized mis-results
  - **Google**: Anti-bot session reuse — migrated from `StealthyFetcher` (new browser per call) to `AsyncStealthySession` (browser reuse + cookie persistence). Added `real_chrome=True`, `block_webrtc=True`, `hide_canvas=True`, `network_idle=True`
  - **Startpage**: Migrated from `StealthyFetcher` to `AsyncStealthySession` for consistency with Google
  - **DuckDuckGo**: Region locking (`kl=us-en`) on both HTML and Lite endpoints
- **Code Deduplication**: Moved `_first()`, `_text()`, `_guess_content_type()` from 8 engine files into `engines/base.py`
- **New Documentation**:
  - `docs/engine_insights.md`: 10 focused scraping insights from trial-and-error
  - `docs/lessons_learned.md`: 14-section comprehensive session log covering rate limits, anti-bot, obfuscated DOM recovery, session vs fetcher decision matrix
- **Codex Agent Support**: 21st agent adapter added
  - OpenAI Codex TOML config (`~/.codex/config.toml`) with `mcp_servers`, `developer_instructions`, `AGENTS.md` auto-discovery, `features.codex_hooks`
- **Agent Harness Improvements**:
  - **Claude Code**: Added `UserPromptSubmit` hook for earlier interception (before tool execution)
  - **Zed**: Fixed from no-op to full MCP support — uses `context_servers` key, adds `tool_permissions.default = "allow"`, model hint updated to `claude-sonnet-4-5`
  - **Windsurf**: Fixed MCP config path from `~/.windsurf/` to official `~/.codeium/windsurf/mcp_config.json`

### Fixed
- **scrapling 0.2.99 compatibility**: Migrated from removed `AsyncDynamicSession` / `AsyncStealthySession` to public `AsyncFetcher` / `StealthyFetcher` APIs
  - Fixed `ImportError: cannot import name 'AsyncStealthySession'` causing `stealthy_fetch` complete failure
  - Fixed timeout unit mismatch: `StealthyFetcher.async_fetch()` uses milliseconds, `AsyncFetcher.get()` uses seconds
  - Fixed `TextHandler` compatibility: `len(element.text)` returns 0 in scrapling 0.2.99; wrapped all `.text` accesses with `str()` to ensure correct string behavior
- **fetch_bulk bot detection improvement**: Sites previously blocked (e.g., `open-harness.dev`, `modelcontextprotocol.io`) now fetch successfully with new scrapling fetchers
- **Blocked error messages**: Added precise, user-actionable guidance based on error classification (timeout, SSL, DNS, 403, import error)
- **All search engines**: Fixed `AsyncFetcher.async_fetch()` → `.get()` in `bing`, `naver`, `searxng`, `startpage`, `qwant`, and `google` (was causing `AttributeError` at runtime)
- **Exception signatures**: `ParseError` and `NetworkError` now properly accept `retryable` and `suggested_engine` kwargs, fixing runtime `TypeError` when engines raise these exceptions
- **Bing redirect decoding**: `resolve_redirect()` now decodes Bing's `/ck/a?...&u=BASE64URL` internal redirect URLs to actual destination URLs
- **Startpage recovery**: Migrated from `AsyncFetcher` to `StealthyFetcher` — Startpage now requires JavaScript rendering. Updated selectors to match new client-side rendered DOM (`div.result`, `.result-title h2`, `.description`)
- **Engine reliability adjustments**: Downgraded `qwant` (0.85→0.30) and `naver` (0.85→0.25) to `quality_tier=3` (last-resort) due to hard bot blocks and DOM obfuscation respectively
- **Removed SearXNG**: All public instances are down; completely removed from codebase
- **Removed Qwant**: Hard "Service unavailable" block regardless of IP/region; completely removed from codebase
- **Removed Brave**: API-only engine requiring `BRAVE_API_KEY`; violates 100% free principle
- **Removed Academic**: API-only engine relying on ArXiv + Semantic Scholar APIs; not direct scraping
- **Added Yahoo Search**: New scraping engine with Yahoo SERP parsing (`div.algo`, `h3 span`, `.compText`) and `/r.search.yahoo.com` redirect decoding
- **Added Ecosia**: New scraping engine with Ecosia SERP parsing (`article.result`, `aria-label`, `.result__description`)
- **Added Baidu**: New scraping engine for China's largest search engine. Uses `mu` attribute for real URLs, `h3` for titles
- **Locale Harness** (`utils/locale_harness.py`): Region-specific query optimization
  - Automatically appends localized keywords for `baidu` (中文) and `naver` (한국어)
  - Detects when query is already in target language and skips transformation
  - Tech-term translation: `documentation` → 文档/문서, `tutorial` → 教程/튜토리얼

### Changed
- Bumped minimum `scrapling` dependency from `>=0.2.0` to `>=0.2.99`

## [0.9.2] - 2025-05-12

### Added
- **3-Layer Real Research Enforcement Architecture**: Technical gatekeeping beyond prompt injection
  - **Layer 1 (Server)**: `SessionEnforcer` — `deep_research` 호출 시 세션에 `research_id` 마킹 + 30min TTL. 나머지 툴은 자유롭게 사용 가능. `generate_code` 툴에서만 `research_id` 검증.
  - **Layer 2 (Client Hooks)**: Physical blocking before agent acts:
    - **Claude Code**: `PreToolUse` hook script (`~/.claude/hooks/maru-enforce-research.sh`) exits 2 to block Write/Edit
    - **Aider**: `lint-cmd` gate script (`~/.maru/aider_research_gate.py`) fails if research incomplete
    - **Cursor**: Custom `/research` and `/verify` slash commands + `.cursorrules` + `settings.json` defaultInstructions + **`.cursor/hooks/onPreEdit`** gate script (2026 Cursor hooks)
    - **Windsurf**: `settings.json` with MCP autoEnable + defaultInstructions
    - **Zed**: `settings.json` assistant.default_instructions hint
    - **Continue**: `/verify` custom command alongside existing `/research`
    - **Hermes**: Full plugin-based enforcement via `hermes_agent.plugins` entry point
      - `pre_tool_call` hook blocks un-researched tools with reason
      - `post_tool_call` hook for audit logging
      - `on_session_start` hook resets gate + injects system message
      - `/research` and `/verify` slash commands
      - `hermes maru status` CLI command
      - Gateway hooks + skills registration
  - **Layer 3 (Tool Dependency)**: `generate_code(research_id=...)` — code generation gated by valid research tokens + citation verification
- **`~/.maru/session_research.json`**: Filesystem marker written by `SessionEnforcer` for client-side hooks to verify research state

### Fixed
- **Python 3.9 compatibility**: Removed `zip(..., strict=False)` in `sanitize.py:322` (strict kwarg added in 3.10)
- **Build**: Removed deprecated `License :: OSI Approved :: MIT License` classifier (setuptools no longer supports classifier-style licenses)

## [0.9.2] - 2025-05-12

### Added
- **10th search engine**: Brave Search support added to the failover cluster
- **Academic engine**: ArXiv + Semantic Scholar specialized engine for research queries
- **MCP Audit Logging**: `harness/audit.py` — SQLite-backed tool call logging with behavioral anomaly detection (rapid-fire, oversized results, suspicious parameters, slow execution)
- **Security hardening**: Expanded from 7 to 72 attack signatures covering Tool Poisoning, Rug Pull, Tool Shadowing, Cross-tool poisoning, MPMA, unauthorized invocation, and `.mcp.json` tampering
- **Docker sandbox support**: `Dockerfile` + `.dockerignore` with non-root user and health checks
- **New CLI commands**: `stats` (KnowledgeStore statistics) and `workflow` (GitHub Actions CI/CD research workflow template)
- **8 new agent adapters**: Zed, JetBrains AI, Supermaven, Cody, Codeium, Amazon Q, Devin, Tabnine (11 → 19 total)
- **Aider quality gates**: Expanded from 4 to 14 languages (Java, Kotlin, C/C++, C#, Ruby, PHP, Swift, Dart/Flutter, Scala, Deno, Biome)

### Fixed
- **Critical bug**: `ResearchResult` cache hit used wrong field names (`engine_used`, `answer`, `query_expansions`) causing `TypeError`
- **Critical bug**: `follow_links` block referenced undefined `search_engine` local variable → changed to `primary_engine`
- **Critical bug**: DuckDuckGo domain check `"github.com" in domain` failed on subdomains → changed to `endswith()`
- **scrapling compatibility**: 6 existing engines migrated from `DynamicFetcher` to `AsyncFetcher`/`StealthyFetcher` for scrapling 0.2.99+

### Changed
- Python 3.10+ syntax: All `typing.Optional` and `typing.List` annotations migrated to `| None` and `list[...]`
- README and landing page fully synchronized with actual feature set
- Architecture diagrams expanded to show all 19 supported agents

## [0.9.1] - 2025-05-07

### Added
- Initial KnowledgeStore SQLite caching layer
- 7-phase deep research pipeline with subquery expansion
- 7 search engine failover (DuckDuckGo, SearXNG, Bing, Naver, Qwant, Google, Startpage)
- 11 agent adapters (Claude, Cursor, Kimi, Windsurf, Aider, Copilot, Continue, Cline, OpenCode, AntiGravity, Kilo)
- Prompt injection defense with 7 initial signatures
- MCP harness setup with automatic rule injection
- BM25 + semantic ranking for search results

## [0.1.0] - 2025-04-28

### Added
- Initial release with basic MCP server scaffold
- DuckDuckGo search integration
