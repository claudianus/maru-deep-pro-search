# 변경 이력 (Changelog)

이 프로젝트의 주요 변경 사항을 여기에 기록합니다.

형식은 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)를 따르며, [Semantic Versioning](https://semver.org/spec/v2.0.0.html)을 준수합니다.

> **참고:** 과거 항목 본문은 국제 검색·호환을 위해 영어로 남겨 두었습니다. 새 항목부터 필요 시 한국어 요약을 병행할 수 있습니다.

## [Unreleased]

## [0.22.4] - 2026-05-20

### Fixed
- **Research gate scope** — Cursor, Claude, Kimi, Antigravity, Windsurf, Cline, Aider 훅이 로컬 읽기·편집·검증까지 `answer`/`deep_research`를 요구하던 과차단을 완화했습니다. 이제 외부 최신성 작업(웹 검색, 네트워크 조회, 패키지 최신 버전 확인)만 fresh research를 요구합니다.
- **`strip_existing_protocol`** — Cursor `maru-research-protocol.md`에서 마커 밖 `# maru-deep-pro-search Research Protocol` H1이 `setup`마다 중복 쌓이던 문제. 재주입 전 stale H1 제거.

## [0.22.3] - 2026-05-19

### Fixed
- **Kimi `config.toml`** — `system_prompt`·`default_yolo` EOF append → nested under last TOML table (예: `mcp.client`). 첫 `[table]` 앞 루트 삽입 + `setup --repair`.
- **Hermes `config.yaml`** — MCP/hooks EOF text append가 `mcp_servers` 밖으로 빠지거나 `hooks:` duplicate로 기존 훅 덮어쓰던 문제. YAML merge로 `mcp_servers`·`plugins`·`hooks.post_tool_call` 병합.
- **공통** — `toml_edit` 헬퍼 추출; Codex adapter도 공유.

## [0.22.2] - 2026-05-19

### Fixed
- **Codex `config.toml`** — `developer_instructions`를 파일 끝에 append하던 버그 수정. 마지막 TOML 테이블(예: `[tui.model_availability_nux]`) 안으로 들어가 Codex Desktop이 `expected u32` 파싱 오류를 내던 문제. 이제 첫 `[table]` 앞 루트에 삽입. nested 감지 시 `setup --repair`로 수리.

## [0.22.1] - 2026-05-19

### Added
- **`warmup-embeddings`** — `maru-deep-pro-search-setup warmup-embeddings`로 Hugging Face 모델 사전 다운로드·probe encode. `install.sh` / `install.ps1`이 패키지 설치 직후 자동 실행.

### Changed
- **`setup`** — 에이전트 설정 후 임베딩 로드만 하던 것을 `warmup_embeddings()`로 통일(다운로드+워밍).

## [0.22.0] - 2026-05-19

### Changed
- **기본 임베딩 모델** — `ibm-granite/granite-embedding-97m-multilingual-r2` (97M, 384-dim). IBM MTEB 다국어 검색 ~60.3 vs e5-small ~50.9. 한국어·코드·짧은 SERP 랭킹에 맞춤.
- **E5 접두사** — Granite에는 미적용. `MARU_EMBEDDING_MODEL=intfloat/multilingual-e5-small` 시 `query:`/`passage:` 자동 복원.

### Migration
- **`.maru/knowledge.db`** — 임베딩 벡터 공간이 바뀌므로 업그레이드 후 `rm .maru/knowledge.db` 또는 knowledge 재저장 권장 (차원은 동일 384).

## [0.21.0] - 2026-05-19

### Added
- **`embeddings` 모듈** — 랭킹·KnowledgeStore·프롬프트 인젝션 탐지가 단일 로컬 모델(`intfloat/multilingual-e5-small`)을 공유합니다. E5 `query:`/`passage:` 접두사를 적용해 검색 품질을 높였습니다.
- **`MARU_EMBEDDING_MODEL`** — Hugging Face 모델 ID로 임베딩 백엔드를 교체할 수 있습니다.

### Changed
- **`sentence-transformers` 필수 의존성** — `pip install maru-deep-pro-search`만으로 시맨틱 랭킹이 항상 활성화됩니다. `setup`·설치 스크립트가 없으면 자동 설치·모델 로드를 검증합니다.
- **보안 임베딩 통합** — 별도 MiniLM 대신 동일 E5 모델로 인젝션 유사도 탐지(모델 1회 로드).

### Removed
- **`MARU_ENABLE_SEMANTIC_INSTALL` opt-in** — 시맨틱은 기본 경로입니다.

## [0.20.0] - 2026-05-19

### Added
- **Research Trace / Insights / Evidence Clusters** — `deep_research` 출력에 조사 과정, 핵심 인사이트, 출처 클러스터, 답변 설계 블록을 추가해 Perplexity Deep Research에 가까운 UI/하네스 소비가 가능해졌습니다.
- **Source quality signals** — 쿼리 커버리지, 필수 엔티티 누락, 접근성/페이월 위험, 노이즈 패널티를 랭킹·receipt·출력 메타데이터에 반영합니다.
- **Stress benchmark suite** — 한국어 초경량 모델 조사, Transformers/ComfyUI 호환성, Apple Silicon LLM 추론, LTX/ComfyUI 워크플로를 포함한 품질 스트레스 벤치를 추가했습니다.

### Changed
- **검색 기본값 상향** — `deep_research` 기본 30개 소스, 7개 서브쿼리, 엔진당 SERP 50개, answer deep 모드 30개 소스/6개 본문 확인으로 조정했습니다.
- **랭킹/중복 제거 개선** — SERP 실행 단위 RRF, fuzzy dedupe 대표 병합, 접근성·노이즈·커버리지 기반 재랭킹으로 동일 엔진 중복과 무관한 구매가이드/홈페이지 노이즈를 줄였습니다.
- **쿼리 확장 개선** — 버전·CVE·숫자 포함 패키지명·한글 토큰 보존, Korean NLP 모델 별칭, Hugging Face `transformers` 모호성 해소, 보안/버전/벤치 각도를 강화했습니다.
- **본문 확인 플래너 개선** — 도메인/출처 타입 다양성, source-family viability, paywall risk를 반영해 `fetch_bulk` 후보를 더 공격적으로 선별합니다.

### Fixed
- **Startpage 자동 추천** — Playwright 비용이 큰 Startpage는 `MARU_ENABLE_STARTPAGE=1`일 때만 자동 추천에 포함합니다.
- **Receipt JSON** — 출처별 score/type/primary/engines/coverage/access/noise/missing metadata를 병행 저장해 후속 툴 체이닝이 가능하게 했습니다.

## [0.19.1] - 2026-05-17

### Fixed
- **cubic PR #94** — compact `unwrap`, `[END EXTERNAL CONTENT]` 경계, `duckduckgo_fetch` recommend 제외, enforcer cap 마커 포함, RRF/cross-engine 중복 제거, gap entity word-boundary, conflicts 다중 출처만, benchmark p95·`engine_failures`, `fetch_bulk(query=)`, answer fetch budget, stealth fallback on `_fetch_body_markdown`.

### Changed
- **AGENTS.md** — cubic pending/open 이슈 시 머지 금지 루프 명시.

## [0.19.0] - 2026-05-17

### Added
- **RRF 융합** — `merge_results`에 reciprocal rank fusion 레이어 (엔진별 순위 합산 후 BM25/메타 보정).
- **`rank_pages` 연결** — `fetch_bulk`가 `query`가 있을 때 본문 재랭킹.
- **벤치 확장** — primary/acceptable 도메인 GT, answer extended 5쿼리, latency p50/p95·tokens_estimated·engine_failures 리포트.
- **환경 변수** — `MARU_DEEP_MAX_SOURCES`, `MARU_SERP_PER_ENGINE_CAP`, `MARU_WRAPPER_TIER`, `MARU_KNOWLEDGE_REUSE_MAX_CHARS`, `MARU_RESEARCH_CONTEXT_MAX_CHARS`, ranker 가중치.

### Changed
- **토큰 효율** — `deep_research` 기본 `max_sources` 30→10; SERP는 `wrap_serp_content`(경량 래퍼); top-8만 긴 snippet.
- **`auto_fetch` / `answer`** — 병렬 fetch, 본문-only preview(래퍼 잘림 버그 수정).
- **성능** — `duckduckgo_fetch` 별도 CB; fetch 캐시 키 통일; trafilatura `asyncio.to_thread`; `domain_stats` 기록.
- **gap_detector** — CVE/semver/연도 엔티티 누락 시 follow-up 제안.
- **MCP prompts** — `tool_selection_guide`·`anti_bot_strategy` 압축.
- **enforcer** — `append_research_context` 8k chars cap.

### Fixed
- KnowledgeStore 24h 히트 시 무제한 반환 → 4k chars cap.

**수동 회귀 게이트:** `uv run python benchmark/search_quality_benchmark.py` — deep_research NDCG@10 ≥ 0.45, Precision@5 ≥ 0.40.

## [0.17.2] - 2026-05-17

### Added
- **`setup --check` 확장** — `cli/doctor.py`: 중복 프로토콜 블록, 낡은 maru-managed 훅, MCP 누락, 레거시 project-scope 경고.
- **`setup --repair`** — 프로토콜 재주입, 커맨드 upsert, 관리 훅 버전 갱신, MCP 재등록 (`--repair-skills`로 SKILL 덮어쓰기 opt-in).
- **`update --with-setup`** — 업그레이드 후 감지된 에이전트 자동 수리 (`MARU_UPDATE_AUTO_SETUP=1` 동일).

### Changed
- **훅 중앙화** — `cli/hooks_templates.py` + `# maru-managed: <version>` 스탬프 (Claude, Windsurf, Kimi, Aider).
- **Continue YAML** — `--repair` 시 중복 protocol rule 제거.
- **업데이트 안내** — PyPI 업그레이드 성공 시 `setup --repair` 안내 문구.

## [0.17.1] - 2026-05-17

### Added
- **`docs/agent_matrix.html`** — 20 adapters × 3-layer enforcement 정적 매트릭스.
- **벤치마크** — 한국어 answer 모드 쿼리(시세·추천) 3건 추가.

## [0.17.0] - 2026-05-17

### Added
- **Evidence spine** — `research/pipeline.py`: `answer`와 `deep_research`가 동일하게 `write_receipt`·`KnowledgeStore`·`_research_id` 푸터 기록.
- **Tiered drift** — lockfile만 변경 시 soft(정보); `pyproject.toml` 등 hard만 재조사 경고.
- **`harness/constants.py`** — `RESEARCH_PRODUCING_TOOLS` 등 단일 상수; server/enforcer/hermes 공유.

### Changed
- **answer-first 문구** — `session_state`, `drift_status`, `query_knowledge`, harness 템플릿, Claude 훅 메시지 통일.
- **`answer` 헤더** — `quality:` 라인(deep_research와 동일 언어).

## [0.16.2] - 2026-05-17

### Fixed
- **`fetch_page` 캐시** — `max_tokens`를 캐시 키에 포함해 answer 소형 fetch가 대형 요청을 오염시키지 않음.
- **Hermes 플러그인** — `RESEARCH_PRODUCING_TOOLS`와 동일 면제 목록; `/ask`·`/research` 안내 문구.
- **Continue setup** — 기존 `ask`/`search`/`compare`/`research` 프롬프트 내용 갱신.

### Documentation
- **GitHub Pages** — v0.16.2·answer-engine 히어로 배지.
- **`AGENT_COMPATIBILITY.md`** — answer-first·리서치 생산 툴·슬래시 커맨드 동기화.
- **`ROADMAP.md`** — 0.16.x 현황 반영.

## [0.16.1] - 2026-05-17

### Fixed
- **cubic PR #89** — Hermes 게이트: 툴 실패 시 `_mark_research` 생략; `query_gate` freshness 대소문자·한국어 filler; `enforcer` 미분류 툴 fail-closed; `server` `[BLOCKED]` 휴리스틱 축소; `answer` fetch 예산·`max_tokens` 정합; `setup` pip 따옴표; Cursor/Claude command 갱신·JSON 폴백; DuckDuckGo scrapling 필터만 인스턴스화.
- **cubic PR #90** — `tool_result.is_successful_tool_result` 공유; Hermes BLOCKED 응답 감지; README `0.16.1` 예시.

## [0.16.0] - 2026-05-17

### Added
- **`answer-engine` skill** — 일반 웹 질문·시세·추천·한국어 소비자 검색용 Perplexity 스타일 진입 가이드.
- **에이전트 커맨드** — Claude/Cursor에 `ask`·`search`·`compare`, Continue에 동명 슬래시 커맨드 추가 (`research`·`verify`와 함께).

### Changed
- **`answer` 툴** — 랭킹 소스·페치 근거가 포함된 answer-engine 패킷으로 강화; 일반 질문은 `answer`, 코드·보안·깊은 조사는 `deep_research` 우선.
- **쿼리 게이트** — 영어/한국어 자연어 질문을 SERP 키워드로 정규화(예: 중고폰 시세 추천 → 최신 시세 검색); 대화체 즉시 거절 완화.
- **`setup` semantic** — 기본 MCP stdio는 조용히 유지; `MARU_ENABLE_SEMANTIC_INSTALL=1`일 때만 `sentence-transformers` 설치 시도 (`MARU_SKIP_SEMANTIC_INSTALL` 대체).
- **하네스·프롬프트** — enforcer·deep-research SKILL·에이전트 어댑터가 answer-first 결정 트리와 동기화.

### Documentation
- **README / README.en / GitHub Pages** — 툴 우선순위, 쿼리 게이트, semantic opt-in, v0.16.0 배지 동기화.

## [0.15.1] - 2026-05-16

### Documentation
- **GitHub Pages (`docs/index.html`)** — 바이브 코더 플레이북·쿼리 게이트 프롬프트 팁·18툴 고밀도 표·ENV 치트시트·내비/히어로/아키텍처 보강, 설치 스니펫에 semantic `--with` 및 `setup`/`init`.
- **README / README.en** — Getting Started 예시 버전 문자열 `0.15.1` 동기화.

### Changed
- **버전** — `pyproject.toml` · `maru_deep_pro_search.__version__` → **0.15.1**.

## [0.15.0] - 2026-05-16

### Added
- **`deep_research` 로캘 하네스** — Naver/Baidu 검색에 `optimize_for_engine`을 적용(영어 기술어 → 로컬 힌트)해, 무과금으로 클러스터 내 SERP 품질을 개선.

### Changed
- **README** — 하네스 `init`, 엄격 쿼리 게이트, `drift_status`, knowledge CLI 문서화; 툴 수 18로 반영. 기본 README는 한국어, 영문은 `README.en.md`.

## [0.14.0] - 2026-05-15

### Added
- **Search Query Gate (strict)** — Rejects conversational/vague `query` strings with rewrite templates; auto-optimizes valid queries (strip filler, fresh year, security/compare/docs hints). Set `MARU_STRICT_QUERY=0` to disable rejection.
- **Rule 14** in research protocol — agents must send keyword-style queries to all search tools.

### Changed
- `deep_research`, `web_search`, `answer`, `parallel_search`, `search_with_citations` run queries through the gate before any network I/O.
- Tool output may include `_query: original → optimized (...)_` when auto-fixed.

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
