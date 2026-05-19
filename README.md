<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>AI 에이전트가 코딩 전에 반드시 리서치하도록.</strong><br>
  API 키 0개 · 9엔진 RRF+BM25 · 인사이트 클러스터 · 네이티브 인용 · 21개 AI 에이전트
</p>

<p align="center">
  <a href="./README.en.md">🇺🇸 English</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/validate.yml?style=flat-square&label=validate" alt="Validate"></a>
  
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-deep-pro-search/">🌐 웹사이트</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## 소개

`maru-deep-pro-search`는 AI 코딩 에이전트에게 **실시간 웹 검색 능력**을 부여하고, 어떤 코드를 작성하기 전에 **반드시 사용하도록 강제**하는 MCP 서버입니다.

| | 에이전트 내장 검색 | maru-deep-pro-search |
|---|---|---|
| **엔진** | 1–2개, 폴오버 없음 | **9엔진 자동 폴오버** |
| **랭킹** | 엔진 기본 순서 | **9엔진 결과를 한 번에 재정렬(RRF+BM25·시맨틱·권위/신선도)** |
| **인용** | 환각 또는 없음 | **`[1]`, `[2]` 네이티브 ID + 실제 URL** |
| **방어** | 없음 | **72시그니처 프롬프트 인젝션 + 제로폭 문자 정제** |
| **강제** | "검색해주세요" (무시됨) | **3계층 기술적 게이트키핑 + 코드 검증** |
| **에이전트** | 범용 | **21개 전용 어댑터 + 스킬 파일 주입** |
| **비용** | 변동 | **영원히 $0 — API 키 불필요** |

---

## 3분 요약

1. **설치** → `maru-deep-pro-search setup` → 사용 중인 에이전트(Cursor, Claude Code 등) **재시작**
2. **일반 질문**(시세·추천·쇼핑) → 에이전트에게 평문으로 *「갤럭시 중고폰 최신 시세」* — 내부적으로 `answer`가 근거와 `[1]` 인용을 모읍니다
3. **코드·보안·설계** → *「FastAPI vs Django 2025 아키텍처 비교」*처럼 기술·깊은 조사 — `deep_research`가 먼저 돌고(기본 **30개** 출처 · 7서브쿼리) 그다음 코드
4. **이미 쓰는 중** → `pip install -U maru-deep-pro-search` 후 `maru-deep-pro-search update --with-setup` (또는 `setup --repair`) → `setup --check`로 확인

---

## ⚡ 10초 설치

**macOS / Linux — 권장 (`uv` 자동 설치):**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**수동 (pip, Python ≥3.10):**
```bash
python3 -m pip install --user maru-deep-pro-search && maru-deep-pro-search setup
```
시맨틱 랭킹(`sentence-transformers` + `ibm-granite/granite-embedding-97m-multilingual-r2`)은 **기본 포함**입니다. `install.sh` / `setup`이 Hugging Face 모델을 **사전 다운로드**해 첫 `deep_research` 콜드스타트를 줄입니다.

**권장 (uv):**
```bash
uv tool install --python 3.12 git+https://github.com/claudianus/maru-deep-pro-search.git
```
PyPI: `uv tool install --python 3.12 maru-deep-pro-search`

설정 마법사가 AI 에이전트를 자동 감지하고, 기존 설정을 백업한 뒤 MCP 설정을 주입하고, 리서치 우선 규칙을 강제합니다.

---

## 🚀 시작하기

### 1. 설치 확인
```bash
maru-deep-pro-search --version
# 예: 0.20.0 (PyPI 최신)
```

### 2. 에이전트 설정
```bash
maru-deep-pro-search setup
```
설치된 에이전트(Claude, Cursor 등)를 자동 감지하고 MCP 설정을 주입합니다.

**업그레이드(이미 설치한 경우)** — `pip install -U`만 하면 에이전트 설정은 자동으로 바뀌지 않습니다.

```bash
pip install -U maru-deep-pro-search
maru-deep-pro-search update --with-setup
# 또는: maru-deep-pro-search setup --repair
maru-deep-pro-search setup --check    # 진단만
```

프로토콜이 중복되거나 훅 문구가 낡았을 때 `setup --repair`를 권장합니다. SKILL 파일까지 덮어쓰려면 `setup --repair --repair-skills`.

### 3. Claude Code용 MCP 설정 예시
`~/.claude/settings.json`에 추가:
```json
{
  "mcpServers": {
    "maru-deep-pro-search": {
      "command": "python3",
      "args": ["-m", "maru_deep_pro_search.server"]
    }
  }
}
```

### 4. 첫 리서치
에이전트에게 *「갤럭시 중고폰 최신 시세」*처럼 일반 질문이면 `answer()`가, *「FastAPI vs Django 2025 아키텍처 비교」*처럼 기술·깊은 조사면 `deep_research()`가 먼저 호출된 뒤 인용이 있는 답을 만듭니다.

### 5. 프로젝트 하네스 (팀·로컬 데이터만)
작업 중인 저장소에 **프로젝트 전용** `.maru/knowledge.db`, `.maru/harness.yaml`, 선택적 `AGENTS.md`만 만들려면:

```bash
maru-deep-pro-search init
```

에이전트(MCP·규칙·스킬)는 **저장소 안에 쓰지 않습니다.** 각 개발 머신에서 한 번 `maru-deep-pro-search setup`으로 **전역(홈 등)** 에만 설정합니다. MCP와 동일한 단위입니다.

워킹 카피에는 `.maru/`와 선택적 `AGENTS.md`만 두고 커밋 정책은 팀에 맡기면 됩니다.

### 6. 검색 쿼리·엄격 게이트

검색 툴은 **키워드형**(제품/라이브러리·주제·연도 등 3–12어절) 쿼리를 선호하지만, 일반 영어/한국어 질문은 가능한 한 먼저 검색용 키워드로 정규화합니다. 예: *「갤럭시 중고폰 최신 시세 추천」*은 거절하지 않고 최신 시세 검색으로 바꿉니다.

- 거절 끄기(최적화만): `export MARU_STRICT_QUERY=0`
- `answer` / `deep_research` 이후 영수증은 `~/.maru/receipts/`에 저장됩니다. **드리프트**는 hard(`pyproject.toml` 등)와 soft(락파일만)로 구분됩니다 — soft만 바뀌면 재조사 경고가 뜨지 않습니다. 웹 없이 확인: `drift_status`.
- 팀 캐시 공유: `maru-deep-pro-search-knowledge export -o bundle.json` / `import bundle.json`

`deep_research`에서 **한글·중문** 쿼리는 네이버/바이두 로컬 하네스로 보강됩니다.

---

## 🏆 다른 도구와 비교

| 항목 | maru-deep-pro-search | Tavily MCP | Perplexity MCP |
|---|---|---|---|
| **비용** | **영구 $0** | 무료 티어 / 검색당 유료 | 최소 $5/월 |
| **엔진** | **9 스크래퍼 + 폴오버** | API 1종 | API 1종 |
| **셀프호스팅** | **✅** | ❌ | ❌ |
| **오프라인** | **✅** (캐시) | ❌ | ❌ |
| **인용** | 네이티브 `[N]` | 있음 | 있음 |
| **리서치 강제** | **3계층 기술 게이트** | ❌ | ❌ |
| **프롬프트 인젝션 방어** | **72패턴 + 시맨틱** | 기본 | 기본 |
| **에이전트 어댑터** | **21개** | 범용 | 범용 |
| **딥리서치 UI** | **Trace·Insights·Clusters** | ❌ | ❌ |

---

## 🛠️ 18개 MCP 툴

### 자주 쓰는 3개

| 툴 | 한 줄 설명 | 예시 질문 |
|------|-----------|-----------|
| `answer` | 일반 웹 질문 — 랭킹된 출처 + 인용 패킷 | 갤럭시 중고 시세, 추천 |
| `deep_research` | 다중 엔진 깊은 조사(기본 30소스) + Trace·Insights·Clusters | 라이브러리 비교, CVE, 아키텍처 |
| `fetch_page` | 찾은 URL 본문 읽기(정제·방어 적용) | 공식 문서 링크 하나만 열기 |

아래 표는 **고급·진단** 툴입니다. 대부분의 작업은 위 세 가지와 에이전트 대화만으로 충분합니다.

### 리서치 코어 (고급)
| 툴 | 용도 | 언제 사용 |
|------|---------|-------------|
| `answer` | Perplexity 스타일 answer-engine 패킷 + 랭킹 소스 + 페치 근거 | 일반 웹 질문, 시세, 추천, 한국어 소비자 검색 |
| `deep_research` | 쿼리 확장 + 다중 엔진 + BM25 랭킹 + **품질 점수** + **자동 페치** | 코드, 아키텍처, 보안, 복잡한 리서치 전 |
| `parallel_search` | 동시 다각도 검색 + 비교 모드 | 다각도 분석 (예: "A vs B") |
| `web_search` | 스크래핑 + 랭킹 + 인용 결과 반환 | 추가 타겟 소스 수집 |
| `search_with_citations` | 학술 작성용 사전 번호 소스 | 논문, 엄격한 인용 필요 시 |

### 페치 & 추출 (고급)
| 툴 | 용도 | 언제 사용 |
|------|---------|-------------|
| `fetch_page` | 단일 URL에서 깨끗한 콘텐츠 추출 (403 자동 스텔스 폴백) | 리서치로 찾은 문서 읽기 |
| `fetch_bulk` | 중복 제거가 포함된 병렬 페치 | 2–10개 URL 동시 읽기 |
| `stealthy_fetch` | 보호된 사이트용 안티봇 우회 | Cloudflare/DataDome 차단 시 (최후 수단) |

### 검증 & 강제 (고급)
| 툴 | 용도 | 언제 사용 |
|------|---------|-------------|
| `generate_code` | **코드 검증 게이트** — 인용 없는 코드 차단 | 리서치 후 — 코드가 인용에 기반하는지 확인 |
| `session_state` | 세션 리서치 상태, 툴 기록, 인용 확인 | 툴이 차단된 이유 디버깅 |
| `drift_status` | 마지막 리서치 이후 매니페스트/에러 드리프트 (웹 검색 없음) | 의존성·에러 패턴 변경 후 |
| `query_knowledge` | 지식 저장소에서 과거 리서치 검색 | 웹 재검색 없이 리서치 재사용 |
| `export_research` | 현재 세션 리서치를 마크다운 파일로 내보내기 | 리서치 결과 저장/공유 |

### 엔진 & 인프라 (진단)
| 툴 | 용도 | 언제 사용 |
|------|---------|-------------|
| `list_engines` | 신뢰도 및 지연 시간 메타데이터와 함께 모든 검색 엔진 나열 | 적합한 엔진 선택 |
| `engine_health` | 실시간 서킷 브레이커 상태 | 검색 실패 진단 |
| `cache_stats` | 인메모리 캐시 적중/실패 통계 | 성능 모니터링 |
| `clear_caches` | 모든 인메모리 캐시 초기화 | 신선한 결과 강제 |
| `version` | 버전 및 업데이트 확인 | 설치 상태 확인 |

**툴 선택 가이드:**
```
사용자 요청?
├── 일반 웹 질문 / 최신 시세 / 추천? → answer(query, mode="balanced")
├── 코드 / 보안 / 아키텍처 / 깊은 조사? → deep_research(query, auto_fetch=3)
│   ├── 기본 max_sources=30; 빠른 작업은 10–15로 낮추기
    ├── 다각도 분석? → parallel_search
    ├── 특정 URL 읽기? → fetch_page / fetch_bulk
    ├── 사이트 차단? → stealthy_fetch (최후 수단)
    ├── 과거 리서치 재사용? → query_knowledge
    ├── 리서치 신선도 확인? → session_state / drift_status
    └── 느린 검색 진단? → cache_stats / engine_health
```

---

## 🤖 21개 AI 에이전트 — 확장 메커니즘 매트릭스

한 번의 설정으로 모든 에이전트의 **확장 표면**에 리서치 우선 규칙을 주입합니다 — hooks, commands, plugins, cron, permissions 등.

| 에이전트 | MCP | Hooks | Commands | Agents/Cron/Plugins | 규칙 / 프롬프트 | Skills | 기타 표면 |
|-------|:---:|:-----:|:--------:|:-------------------:|-----------------|--------|-----------|
| **Claude Code** | ✅ | 4개 라이프사이클 훅 | `ask.md` `search.md` `compare.md` `research.md` `verify.md` | — | `CLAUDE.md` + hooks | `~/.claude/skills/` nested | 권한 deny 패턴 |
| **Cursor** | ✅ | — | `ask.json` `search.json` `compare.json` `research.json` `verify.json` | — | `.cursor/rules/*.md` | `~/.cursor/rules/` flat | `autoEnableTools` |
| **Kimi** | ✅ | `PreToolUse` (TOML) | — | — | `config.toml` `system_prompt` | `~/.kimi/skills/` nested | `default_yolo=false` |
| **Cline** | ✅ | `PreToolUse.py` | — | `maru-research-gate.md` 에이전트 + `.cron.md` | `.clinerules/*.md` | `~/.cline/skills/` flat | — |
| **Continue** | ✅ | — | `ask` `search` `compare` `research` `verify` | — | `system_message` + `.continue/rules/` | `~/.continue/rules/` flat | — |
| **Windsurf** | ✅ | 3개 Cascade 훅 | — | — | `.windsurf/rules/*.md` + `AGENTS.md` | `~/.windsurf/rules/` flat | `.codeiumignore` |
| **Zed** | ✅ | — | — | — | `.rules` + `assistant.md` | — | `tool_permissions` |
| **JetBrains** | ⚠️ | — | — | — | `.idea/ai-assistant-rules/*.md` | `.idea/ai-assistant-rules/` flat | — |
| **Cody** | ⚠️ | — | — | — | `.cody/prompts.md` | — | — |
| **Devin** | ⚠️ | — | — | — | `.devin/rules.md` | — | — |
| **Amazon Q** | ⚠️ | — | — | — | `.amazonq/rules/*.md` | `.amazonq/rules/` flat | — |
| **Tabnine** | ⚠️ | — | — | — | `.tabnine/guidelines/*.md` | `.tabnine/guidelines/` flat | — |
| **Codeium** | ⚠️ | — | — | — | `.codeium/system-prompt.md` | — | — |
| **Copilot** | ⚠️ | — | — | — | `.github/copilot-instructions.md` | — | — |
| **Aider** | ⚠️ | — | — | — | `CONVENTIONS.md` + `.aider.conf.yml` | — | Lint-cmd gate, architect mode |
| **Codex** | ✅ | `codex_hooks` | — | — | `AGENTS.md` + `developer_instructions` | — | `approval_policy` |
| **Kilo** | ✅ | — | — | — | `kilo.jsonc` `systemPrompt` + `instructions` | `~/.config/kilo/rules/` flat | `experimental.codebase_search` |
| **OpenCode** | ✅ | — | — | `maru-research-gate` 에이전트 | `AGENTS.md` + `opencode.json` agents | — | — |
| **AntiGravity** | ✅ | — | — | — | `~/.gemini/antigravity/config.json` | — | — |
| **Hermes** | ✅ | Gateway + Shell 훅 | — | `maru-research-gate` 플러그인 + cron | `SOUL.md` + `config.yaml` | `~/.hermes/skills/` flat | 플러그인 시스템 |
| **Supermaven** | ⚠️ | — | — | — | `.supermaven/rules.md` | — | — |

> **범례:** ✅ = 전체 MCP 지원 · ⚠️ = 규칙 주입만 (네이티브 MCP 없음)
>
> **Hooks** = PreToolUse / PostToolUse / SessionStart / pre_write_code / pre_mcp_tool_use / pre_user_prompt / 등  
> **Commands** = 슬래시 커맨드 또는 에이전트 설정에 등록된 커스텀 커맨드  
> **Agents/Cron/Plugins** = 커스텀 에이전트, 크론 스펙, 또는 플러그인 시스템  
> **Skills** = `nested` = `skills/<name>/SKILL.md` · `flat` = `rules/<name>.md`

---

## 🏛️ 아키텍처

```
MCP 클라이언트 (Claude, Cursor, Kimi, Windsurf, ...)
        │ JSON-RPC 2.0 / stdio
        ▼
┌──────────────────────────────────────────────────────────────┐
│  maru-deep-pro-search MCP 서버                               │
│  ├─ 18개 툴 (검색, 페치, 인용, 검증, 인트로스펙션)           │
│  ├─ 9엔진 폴오버 + SERP 단위 RRF 융합 (기본 30소스 · 7서브쿼리) │
│  ├─ 하이브리드 랭킹 (RRF + BM25 + 시맨틱 + 커버리지/접근성)   │
│  ├─ 3계층 강제 + 리서치 품질 점수 (A-F)                        │
│  ├─ 72시그니처 정제 + 제로폭 문자 방어                         │
│  ├─ SQLite 지식 저장소 (정확일치 → FTS → 시맨틱)             │
│  ├─ 인메모리 TTL 캐시 (검색 5분 / 페치 10분)                   │
│  └─ 자동 세션 정리 + 감사 로깅                                 │
└──────────────────────────────────────────────────────────────┘
```

### 3계층 강제 아키텍처

1. **MCP 프롬프트 주입** — `always_research_first()` 프롬프트가 일반 질문은 `answer`, 코드·보안·깊은 조사는 `deep_research`를 유도
2. **세션 게이트** — 서버 `SessionEnforcer`가 연구 의존 툴을 차단하고, `generate_code()`가 `research_id`·인용을 검증
3. **에이전트 규칙** — `setup`이 홈 등 **전역** 경로의 설정 파일에 리서치 프로토콜을 주입(저장소 루트의 `.cursor/` 등에는 쓰지 않음)

서버에 **생성형 LLM은 없습니다**. 추론·종합은 에이전트의 LLM이 담당하고, 서버는 검색 품질·랭킹·추출에 집중합니다.

기술 심화 내용은 [`docs/engine_insights.md`](./docs/engine_insights.md), 운영 교훈은 [`docs/lessons_learned.md`](./docs/lessons_learned.md)를 참고하세요.

### KnowledgeStore

SQLite 기반 연구 캐시 (`./.maru/knowledge.db`):

- **중복 제거** — 동일 쿼리는 `query_hash` 기준 UPSERT (`access_count` 증가)
- **3단계 검색** — 정확 일치 → FTS5 전문 검색 → 시맨틱 유사도 (로컬 Granite 97M R2, 384-dim)
- **도메인 통계** — 도메인별 성공률·평균 응답 시간
- **정리(Prune)** — 30일 이상 항목 자동 삭제

`maru-deep-pro-search stats`로 조회합니다.

> **v0.22+ 임베딩 변경:** 기본 모델이 Granite 97M R2로 바뀌면 기존 `.maru/knowledge.db` 시맨틱 벡터는 무효합니다. `rm .maru/knowledge.db` 후 재검색하거나 그대로 두면 exact/FTS만 쓰다가 새 항목부터 재임베딩됩니다.

---

## 📋 출력 예시

<details>
<summary><b>deep_research</b> — 다중 엔진 랭킹 결과</summary>

```markdown
## Research: FastAPI vs Django 2025
_engines: duckduckgo_lite, bing, yahoo_
quality: 87 (A)

### Research Trace
_deep research: 28 sources analyzed | 7 steps complete | 22 open-access candidates_
1. Query intent normalized and expanded into 5 orthogonal searches
2. 28 deduplicated sources analyzed across 3 engines
...

### Insights
- [1] **FastAPI Documentation** (official docs) — FastAPI is a modern, high-performance web framework...
- [2] **Django 5.1 Release Notes** (official docs) — Django 5.1 adds async ORM improvements...

### Evidence Clusters
- official docs: [1], [2] (avg coverage 82%)
- community: [3], [4] (avg coverage 61%)

### Sources
#### [1] FastAPI Documentation — fastapi.tiangolo.com
_score: 0.92 | [OFFICIAL-DOCS] | engines: 2 | coverage: 0.89 | access: open

### Answer Blueprint
- Start with a direct recommendation/answer in the first paragraph.
- Primary anchors to cite first: [1], [2]
```
</details>

<details>
<summary><b>answer</b> — Perplexity 스타일 직접 답변</summary>

```markdown
## Answer: What is the best Python web framework in 2025?

**FastAPI** is the dominant choice for API-first services, while **Django** remains king for full-stack applications with admin needs.

**Key differences:**
- Performance: FastAPI is ~3× faster due to async native design [1]
- Ecosystem: Django has 15+ years of plugins and battle-tested ORM [2]
- Learning curve: FastAPI is simpler for API developers; Django requires more upfront investment [3]

**When to choose which:**
- API / microservices → FastAPI
- Full-stack with admin → Django
```
</details>

<details>
<summary><b>generate_code</b> — 검증 게이트(리서치 없는 코드 차단)</summary>

```markdown
❌ CODE GENERATION BLOCKED — Research validation failed

Research query: Python asyncio best practices
Research age: 42s

Citations found in your code:
  (none)

ACTION REQUIRED:
1. Run deep_research() on your topic
2. Include [N] citations from research in your code
3. Call generate_code() again with validated code
```
</details>

---

## 🔒 보안

가져온 콘텐츠는 72패턴 방어 계층을 거쳐 LLM에 전달됩니다.

- 제로폭 문자 제거 (`\u200b`, `\u200c`, `\u200d`)
- 채팅 토큰 중화 (`Human:`, `Assistant:` → `[REDACTED]`)
- MCP 특정 공격 탐지 (툴 포이즈닝, 럭 풀, 섀도잉)
- 시맨틱 유사도 기반 인젝션 탐지 (Granite 임베딩)

모든 툴 호출은 `.maru/audit.db`에 기록되며, 급발사·과대 결과·의심 파라미터 등 이상 징후를 탐지합니다.

보고 정책은 [`SECURITY.md`](./SECURITY.md)를 참고하세요.

---

## ⚙️ 설정

환경 변수는 모두 선택입니다. 검색·타임아웃·기본 엔진/한도는 `src/maru_deep_pro_search/config.py`의 `SearchConfig.from_env()` → `DEFAULT_CONFIG`로 읽히며, MCP 툴(`server.py` 시그니처 + `tools.py`)과 SERP용 `with_retry`가 이를 사용합니다. (`pydantic-settings`를 쓰지 않습니다.)

| 환경 변수 | 기본값 | 적용 범위 |
|-----------|--------|-----------|
| `MARU_SEARCH_ENGINE` | `duckduckgo_lite` | MCP `web_search` / `search_with_citations` / `answer` / `parallel_search` / `deep_research` 기본 엔진 |
| `MARU_SEARCH_MAX_RESULTS` | `10` | 검색 툴의 `max_results` 기본값. `answer`는 모드별 기본 소스 수를 사용 |
| `MARU_DEEP_MAX_SOURCES` | `30` | `deep_research` 기본 `max_sources` |
| `MARU_DEEP_MAX_SUBQUERIES` | `7` | `deep_research` 쿼리 확장 상한 |
| `MARU_SERP_PER_ENGINE_CAP` | `50` | 엔진당 SERP 파싱 상한 |
| `MARU_ANSWER_BALANCED_MAX_SOURCES` | `14` | `answer(mode="balanced")` 내부 리서치 최소 소스 수 |
| `MARU_ANSWER_DEEP_MAX_SOURCES` | `30` | `answer(mode="deep")` 내부 리서치 최소 소스 수 |
| `MARU_ANSWER_DEEP_FETCH_COUNT` | `6` | `answer(mode="deep")` 자동 본문 확인 수 |
| `MARU_WRAPPER_TIER` | `tiered` | `tiered`(SERP 경량 래퍼) 또는 `full` |
| `MARU_ENABLE_STARTPAGE` | (미설정) | `1`이면 Playwright 기반 Startpage를 자동 엔진 추천에 포함 |
| `MARU_KNOWLEDGE_REUSE_MAX_CHARS` | `4000` | KnowledgeStore 캐시 히트 응답 상한 |
| `MARU_RESEARCH_CONTEXT_MAX_CHARS` | `8000` | enforcer 세션 research 누적 상한 |
| `MARU_SEARCH_MAX_CONCURRENT` | `5` | `fetch_bulk`의 `max_concurrent` 기본값 |
| `MARU_SEARCH_RETRIES` | `3` | Bing/Yahoo 등 SERP `with_retry` 최대 시도 횟수 |
| `MARU_SEARCH_TIMEOUT` | `30.0` | SERP 스크레이프 (`web_search`, `search_with_citations`), 초 |
| `MARU_FETCH_HTTP_TIMEOUT` | `20.0` | `fetch_page` / `fetch_bulk` URL당, 초 |
| `MARU_DEEP_RESEARCH_TIMEOUT` | `60.0` | `deep_research` 파이프라인, 초 |
| `MARU_DEEP_SERP_RUN_TIMEOUT` | `10.0` | `deep_research` 내부 하위 검색 1회당, 초 |
| `MARU_ANSWER_TIMEOUT` | `60.0` | `answer` 툴, 초 |
| `MARU_AUTO_FETCH_TIMEOUT` | `8.0` | `deep_research`의 `auto_fetch` 안 nested fetch, 초 |
| `MARU_EMBEDDING_MODEL` | `ibm-granite/granite-embedding-97m-multilingual-r2` | 로컬 시맨틱 랭킹·KnowledgeStore·보안 탐지용 Hugging Face 모델 ID |
| (수동 워밍) | — | `maru-deep-pro-search-setup warmup-embeddings` |
| `MARU_SKIP_UPDATE_CHECK` | (미설정) | 값이 비어 있지 않으면 시작 시 PyPI 업데이트 알림 생략 |
| `MARU_DEBUG` | (미설정) | `1`/`true`/`yes`이면 MCP 서버 로그를 DEBUG로 |

그 외: 엄격 쿼리 게이트는 `MARU_STRICT_QUERY`, Hermes/Aider 세션 TTL은 `MARU_RESEARCH_TTL` — 본문 앞쪽·에이전트 문서를 참고하세요.

---

## 💻 CLI 명령어

```bash
# MCP 서버 (stdio 전송)
maru-deep-pro-search

# AI 에이전트 설정 + 스킬 파일 설치
maru-deep-pro-search setup
maru-deep-pro-search setup --check
maru-deep-pro-search setup --repair
maru-deep-pro-search setup --list
maru-deep-pro-search setup --restore
maru-deep-pro-search update --with-setup
# 업그레이드 후: maru-deep-pro-search setup --check

# 프로젝트 하네스 초기화 (.maru만; 에이전트 설정은 하지 않음)
maru-deep-pro-search init

# 헤드리스 딥 리서치 (CI/CD 지원)
maru-deep-pro-search research "FastAPI vs Django 2025" \
  --output report.md --max-sources 8

# 자동 업데이트
maru-deep-pro-search update
maru-deep-pro-search update --check
```

---

## 🐳 Docker

```bash
# 빌드
docker build -t maru-search .

# stdio 전송으로 실행
docker run --rm -i maru-search

# 지속적인 지식 저장소와 함께 실행
docker run --rm -i -v $(pwd)/.maru:/app/.maru maru-search
```

---

## 🆕 v0.20.0 하이라이트

- **Research Trace / Insights / Evidence Clusters / Answer Blueprint** — Perplexity Deep Research에 가까운 구조화 출력 (서버 LLM 없음)
- **출처 품질 시그널** — `coverage`, `access`, `noise`, `missing` 메타가 랭킹·receipt·출력에 반영
- **기본값 상향** — `deep_research` 30소스 · 7서브쿼리 · 엔진당 SERP 50 · `answer(deep)` 30소스/6 fetch
- **SERP 단위 RRF + fuzzy dedupe** — 동일 엔진 중복·구매가이드 노이즈 감소
- **Stress benchmark** — `MARU_BENCHMARK_SUITE=stress`로 한국어·Transformers·Apple Silicon 등 품질 스트레스 검증

> **트레이드오프:** 다중 엔진 + 30소스는 품질이 올라가지만 응답 시간은 단일 엔진 대비 ~2배입니다. 빠른 작업은 `max_sources=10` 또는 `web_search`를 쓰세요.

---

## 🔍 검색 엔진 (9 + fetch)

| 엔진 | 용도 |
|------|------|
| `duckduckgo_lite` | 기본 SERP (가벼움) |
| `duckduckgo` | DDG 풀 버전 |
| `bing`, `yahoo`, `google`, `ecosia` | 글로벌 폴오버 |
| `naver`, `baidu` | 한·중 로케일 부스트 |
| `startpage` | Playwright — `MARU_ENABLE_STARTPAGE=1`일 때만 자동 추천 |
| `duckduckgo_fetch` | fetch 전용 (SERP 추천 제외) |

---

## 📊 벤치마크

```bash
uv run python benchmark/search_quality_benchmark.py
MARU_BENCHMARK_SUITE=stress uv run python benchmark/search_quality_benchmark.py
```

다중 엔진 vs 단일 엔진 (TREC 표준, 10쿼리): Precision@5 **+86%** · NDCG@10 **+36%** · MRR **+25%**

---

## 🆘 문제 해결

**검색 엔진에서 결과가 없음**
```bash
MARU_SEARCH_ENGINE=bing maru-deep-pro-search
```

**설정 마법사가 에이전트를 감지하지 못함**
```bash
maru-deep-pro-search setup --agents cursor
maru-deep-pro-search setup --list
```

**메모리 사용량 높음**
```bash
MARU_SEARCH_MAX_RESULTS=5 maru-deep-pro-search
```

**내 에이전트에서 SKILL.md가 "미지원"으로 표시됨**
> 스킬 디렉터리가 없는 에이전트(Copilot, JetBrains 등)에서는 정상입니다. 규칙은 해당 설정 파일로 주입됩니다. Cursor, Kimi, Claude, Cline, Continue, Windsurf, Kilo, Tabnine, Hermes 등에서 스킬 설치가 ✓로 표시됩니다.

---

## 🤝 기여하기

PR 환영합니다. 개발 환경, 엔진·어댑터 추가는 [`CONTRIBUTING.md`](./CONTRIBUTING.md)를 보세요.

---

## 📄 라이선스

MIT — [`LICENSE`](./LICENSE) 참조.
