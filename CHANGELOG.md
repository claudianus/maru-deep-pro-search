# Changelog

All notable changes to this project will be documented in this file.

## [0.8.1] - 2026-05-10

### Changed
- **Docs from scratch**: README and GitHub Pages completely rewritten
  - README: 400+ lines → ~100 lines. Core message only.
  - GitHub Pages: Nuxt replaced with static HTML (`docs/index.html`). No build step.
- **One-liner install scripts**: `scripts/install.sh` and `scripts/install.ps1`
  - macOS/Linux: `curl | bash`
  - Windows: `irm | iex`
  - Installs package + runs setup wizard in one step
- **pyproject.toml cleanup**: SPDX license string, fixed URLs, setuptools>=77.0

## [0.8.0] - 2026-05-10

### Added
- **Complete rebrand**: `maru-search` → `maru-deep-pro-search`
  - Package name, module name, CLI entry points, MCP server name all updated
- **`maru-deep-pro-search setup` CLI**: One-click agent configuration
  - Auto-detects 7 AI agents: Claude Code, Cursor, Kimi, AntiGravity, Kilo Code, OpenCode, Windsurf
  - Registers maru-deep-pro-search MCP server in each agent's config
  - Injects unskippable "research-first" protocol into system prompts / rules
  - Backs up original configs (restore with `--restore`)
- **Stale year sanitizer**: Automatically removes outdated years from search queries
  - Replaces 2024, 2023, etc. with "latest" to prevent stale results
  - Applied to all search entry points (`deep_research`, `web_search`, `parallel_search`)
- **`suggested_followups` in `deep_research`**: Gap detection for iterative research
  - Analyzes crawled sources to identify uncovered topics
  - Suggests 2-3 follow-up queries (e.g., "benchmark", "tutorial", "troubleshooting")
  - Enables agent-level iterative research loops (Perplexity-style)
- **New CLI module**: `src/maru_deep_pro_search/cli/` with agent adapters
- **New utility**: `utils/query_sanitize.py` for query cleaning
- **New research module**: `research/gap_detector.py` for follow-up suggestion

### Changed
- All internal imports updated from `maru_search` to `maru_deep_pro_search`
- `pyproject.toml`: version 0.8.0, new entry points
- AGENTS.md: Updated architecture and project structure

## [0.7.1] - 2026-05-10

### Fixed
- **Python version requirement**: Corrected `requires-python` from `>=3.9` to `>=3.10`
  - Root cause: Core dependency `mcp>=1.0.0` requires Python 3.10+, causing `ResolutionImpossible` on Python 3.9
  - Removed `"Programming Language :: Python :: 3.9"` classifier
  - Updated AGENTS.md test count: 124 → 164

## [0.7.0] - 2026-05-10

### Added
- **Zero Trust Prompt Injection Defense**: Complete rewrite of sanitize module
  - **Metadata tagging + Agent delegation model** (instead of silent censorship)
  - `analyze_content()` → returns transparent `RiskReport` with:
    - Risk level: LOW / MEDIUM / HIGH / CRITICAL
    - Warnings: zero-width chars, chat tokens, mixed scripts, signatures
    - 10-language attack signature DB (en, ko, zh, ja, ru, es, fr, de, ar, pt)
    - Cyrillic lookalike normalization
    - Optional embedding-based detection via sentence-transformers
  - `wrap_external_content()` → wraps content in structural boundaries:
    - `[EXTERNAL CONTENT]` header with source URL
    - Risk level emoji indicator
    - Sanitization report
    - **SECURITY REMINDER FOR AGENT**: explicit warning not to trust the content
    - `[END EXTERNAL CONTENT]` footer
  - Applied to all tool outputs with actual source URLs
  - MCP prompt `always_research_first` updated with security protocol section

### Changed
- README.md: Security & Privacy table updated
- AGENTS.md: Architecture decisions updated with Zero Trust model
- `tools.py`: All tools now pass real source URLs to `wrap_external_content()`

## [0.6.3] - 2026-05-10

### Added
- **Prompt Injection Defense**: Sanitize all fetched content before LLM injection
  - `utils/sanitize.py`: `sanitize_for_llm()` function
  - Removes zero-width characters (U+200B, U+200C, U+200D, U+FEFF)
  - Removes control characters
  - Neutralizes chat format tokens (<|im_start|>, <|im_end|>, <|system|>, etc.)
  - Detects and replaces suspicious patterns:
    - "Ignore all previous instructions"
    - "You are now DAN / Do Anything Now"
    - "Reveal your system prompt"
    - "=== SYSTEM ===", "=== INSTRUCTION ==="
    - "From now on, you will/must/are"
  - Applied to all tool outputs: web_search, deep_research, fetch_page, fetch_bulk

### Changed
- README.md: Security & Privacy table updated with prompt injection row
- AGENTS.md: Added prompt injection defense to architecture decisions

## [0.6.2] - 2026-05-10

### Added
- **TTL Cache Layer**: In-memory LRU cache to eliminate redundant scraping
  - `utils/cache.py`: `TTLCache` with configurable maxsize and TTL
  - Search cache: 200 entries, 5 min TTL (web_search, deep_research, answer)
  - Fetch cache: 100 entries, 10 min TTL (fetch_page, fetch_bulk)
  - Cache keys include all parameters for precise invalidation
- **Smart Engine Selection + Fuzzy Dedupe**: Reduce token waste from duplicate results
  - Engine quality metadata: `quality_tier`, `typical_latency_ms`, `reliability_score`
  - `SearchEngineRegistry.recommend_engines()`: Auto-selects top 2-3 engines
  - Multi-engine `deep_research`: Primary engine for depth, secondary for breadth
  - Jaccard similarity fuzzy dedupe on titles/snippets (threshold: 0.72)
- **Tests**: 147 passing (was 138), 9 new cache tests + 3 fuzzy dedupe tests

## [0.6.1] - 2026-05-10

### Added
- **Startpage Engine**: 8th search engine — Google results via privacy proxy
  - HTML scraping, no API key, supports stealth mode
  - Registered in SearchEngineRegistry as "startpage"
- **Tests**: 134 → 135 tests (added Startpage engine registration test)

### Changed
- README.md: 7 → 8 search engines table
- AGENTS.md: Updated project structure with all engine files
- docs Mermaid diagram: Added Startpage node

## [0.6.0] - 2026-05-10

### Added
- **Research-First Enforcement**: MCP prompts, tool descriptions, and TOOL_GUIDANCE designed to FORCE agents to research before coding
  - `always_research_first` MCP prompt: MANDATORY protocol with Rule Zero, The Law, Research Checklist
  - Enhanced `deep_research` tool description: "🔴 MANDATORY FIRST STEP for ALL technical requests"
  - Strengthened `TOOL_GUIDANCE`: "NEVER write code based solely on training data"
- **4th MCP Prompt**: `always_research_first` joins existing `tool_selection_guide`, `anti_bot_strategy`, `research_workflow`
- **Documentation**:
  - README.md: Agent Configuration section with per-client setup (Claude Code, Cursor, Kimi CLI)
  - README.md: Comparison table (maru-search vs Perplexity API vs SerpAPI vs Google Custom Search)
  - README.md: Real-World Usage / Vibe Coder scenarios section
  - README.md: Security & Privacy comparison table
  - AGENTS.md: "Forcing Agents to Research Before Coding" section with 3 enforcement mechanisms
- **GitHub Pages**:
  - `docs/public/readme.html`: index.html copy with auto-generation comment
  - `docs/public/404.html`: SPA fallback with redirect to `/maru-search/`

### Changed
- `tools.py`: TOOL_GUIDANCE rewritten for aggressive research-first behavior
- `tools.py`: All tool descriptions tagged with `[POST-RESEARCH]`, `[SUPPLEMENTAL]`, `[MANDATORY FIRST STEP]`
- `server.py`: Prompt count 3 → 4
- README.md: Architecture table updated (3 prompts → 4 prompts)
- Tests: All 134 tests passing (added tool guidance assertions)

## [0.5.2] - 2026-05-10

### Changed
- docs: Remove AI slop, update README and GitHub Pages content
- docs: Fix Korean wording ("100% 묣" → "100% 공짜")
- docs: Add Korean to README, auto language detection on GitHub Pages

## [0.5.1] - 2026-05-10

### Changed
- Lower Python requirement to >=3.9 by replacing PEP 604 union types with Optional

## [0.5.0] - 2026-05-10

### Added
- **Universal AI Search MCP**: Rebranded from clco-deep-research-mcp to maru-search
- **Perplexity-Level Quality**:
  - `answer` tool: Direct cited answers like Perplexity with inline [1], [2] citations
  - `search_with_citations` tool: Citation-ready search results for academic/technical writing
  - BM25 + metadata cross-engine ranking via `research/ranker.py`
  - Answer synthesis: Rule-based summary generation from fetched sources
- **Multi-Engine Architecture**:
  - `SearchEngineRegistry`: Factory pattern for plug-and-play search engines
  - `SearchEngine` ABC with cross-engine metadata (`engines_found`, `cross_engine_score`)
  - Ready for Brave, SearXNG, and other engine additions
- **Configuration System**:
  - `config.py`: Environment-variable based configuration
  - `SearchConfig.from_env()`: `MARU_SEARCH_ENGINE`, `MARU_SEARCH_MAX_RESULTS`, etc.
- **Citation-Native Output**:
  - All search results include citation IDs
  - `CitedSource` dataclass for structured source attribution
  - `format_for_llm()` renders Perplexity-style markdown with citations

### Changed
- **Brand**: clco-deep-research-mcp → maru-search (package, module, CLI, MCP server name)
- **Architecture**: DuckDuckGo hard-coding removed from tools.py; uses `SearchEngineRegistry`
- **Deep Research**: Now uses intelligent ranker for result ordering
- **Query Expansion**: Year templates auto-update to current year
- **Code Quality**: Removed duplicate `research/extractor.py`, `engines/code_aware.py`
- **Tests**: 113 → 124 tests (added ranker, config tests)

## [0.4.0] - 2026-05-08

### Added
- **Smart Token Management**: Dynamic token allocation based on source quality
  - `_allocate_tokens()`: High-quality sources get 100% budget, medium 70%, low 40%
  - `max_total_tokens` parameter (default: 20000) for total output budget control
  - `summarize=True` enables extractive summarization for over-budget scenarios
  - `_extractive_summarize()`: Preserves headings and key paragraphs
- **Enhanced Korean Support**:
  - Korean query auto-detection (한글 characters + keywords)
  - Korean-specific query templates: korean_community, korean_docs
  - Korean authority domains: velog.io, tistory.com, naver.com, brunch.co.kr, okky.kr
  - Korean content type classification for developer blogs
- **AI Agent Tool Guidance**:
  - `TOOL_GUIDANCE`: Comprehensive tool selection guide with decision tree
  - 3 MCP prompts: `tool_selection_guide`, `anti_bot_strategy`, `research_workflow`
  - Enhanced tool descriptions with BEST FOR / NOT FOR / TRY FIRST / LAST RESORT labels
  - Performance ranking and common mistakes documentation
- **Increased Token Defaults**:
  - fetch_page: 3000 → 6000
  - fetch_bulk: 1500 → 3000
  - stealthy_fetch: 3000 → 6000
  - deep_research per-source: 1500 → 2500

### Changed
- Tool registry descriptions now include usage scenarios and decision criteria
- README updated with Tool Selection Guide, MCP Prompts section, and v0.4.0 features
- GitHub Pages updated with v0.4.0 stats and features
- Test suite expanded: 68 → 113 tests

## [0.3.0] - 2026-05-08

### Added
- Query expansion: 3-5 orthogonal subqueries for broader coverage
- Relevance scoring: Authority + content type + freshness + position
- Structured exception hierarchy: 7 exception classes with retry hints
- Fault-tolerant CSS selectors with multiple fallbacks
- Package detection: Extract package/library references from code
- URL normalization and filtering utilities
- Exponential backoff retry mechanism
- 21 language detection (up from 16)
- New test suite: 68 tests (up from 35)
- GitHub Pages website

### Changed
- Improved deep research pipeline with multi-pass crawling
- Enhanced error handling with engine fallback
- Better content extraction with trafilatura
- Updated README with v0.3.0 features

## [0.2.2] - 2025-05-07

### Added
- Initial test suite (35 tests)
- Code-aware analysis module
- DuckDuckGo SERP scraping
- Basic deep research pipeline

## [0.2.0] - 2025-05-07

### Added
- Initial release
- 6 MCP tools: web_search, fetch_page, fetch_bulk, deep_research, stealthy_fetch, parallel_search
- Scrapling integration
- trafilatura content extraction
