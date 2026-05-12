# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **3-Layer Real Research Enforcement Architecture**: Technical gatekeeping beyond prompt injection
  - **Layer 1 (Server)**: `SessionEnforcer` — per-session research tracking with 30min TTL. Gated tools return hard error if `deep_research` not called.
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
  - **Layer 3 (Tool Dependency)**: Roadmap — `generate_code(research_id=...)` requiring valid session tokens
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
