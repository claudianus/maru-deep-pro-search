<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>AI 에이전트가 코딩 전에 반드시 리서치하도록.</strong><br>
  API 키 0개 · 9엔진 폴오버 · BM25+시맨틱 랭킹 · 네이티브 인용 · 21개 AI 에이전트
</p>

<p align="center">
  <a href="./README.md">🇺🇸 English</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/test.yml?style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/test.yml"><img src="https://img.shields.io/badge/coverage-59%25-yellow?style=flat-square" alt="Coverage"></a>
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
| **랭킹** | 엔진 기본 순서 | **BM25 + 시맨틱 + 권위도/신선도/코드밀도** |
| **인용** | 환각 또는 없음 | **`[1]`, `[2]` 네이티브 ID + 실제 URL** |
| **방어** | 없음 | **72시그니처 프롬프트 인젝션 + 제로폭 문자 정제** |
| **강제** | "검색해주세요" (무시됨) | **3계층 기술적 게이트키핑 + 코드 검증** |
| **에이전트** | 범용 | **21개 전용 어댑터 + 스킬 파일 주입** |
| **비용** | 변동 | **영원히 $0 — API 키 불필요** |

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

**수동 (pip):**
```bash
pip install maru-deep-pro-search[semantic] && maru-deep-pro-search setup
```

설정 마법사가 AI 에이전트를 자동 감지하고, 기존 설정을 백업한 뒤 MCP 설정을 주입하고, 리서치 우선 규칙을 강제합니다.

---

## 🛠️ 10개 MCP 툴

| 툴 | 용도 | 언제 사용 |
|------|---------|-------------|
| `deep_research` | 쿼리 확장 + 다중 엔진 + BM25 랭킹 심층 검색 | **🔴 항상 먼저** — 코드, 아키텍처, 기술 결정 전 |
| `answer` | Perplexity 스타일 직접 답변 + 인라인 인용 | 리서치 후 빠른 사실 확인 |
| `parallel_search` | 동시 다각도 검색 + 비교 모드 | 다각도 분석 (예: "A vs B") |
| `web_search` | 스크래핑 + 랭킹 + 인용 결과 반환 | 추가 타겟 소스 수집 |
| `search_with_citations` | 학술 작성용 사전 번호 소스 | 논문, 엄격한 인용 필요 시 |
| `fetch_page` | 단일 URL에서 깨끗한 콘텐츠 추출 | 리서치로 찾은 문서 읽기 |
| `fetch_bulk` | 중복 제거가 포함된 병렬 페치 | 2–10개 URL 동시 읽기 |
| `stealthy_fetch` | 보호된 사이트용 안티봇 우회 | Cloudflare/DataDome 차단 시 (최후 수단) |
| `generate_code` | 연구 인용 대비 코드 검증 | 리서치 후 — 미검증 코드 차단 |
| `version` | 버전 및 업데이트 확인 | 설치 상태 확인 |

**툴 선택 가이드:**
```
기술적 요청이 있음?
└── deep_research(query) 먼저
    ├── 빠른 확인 필요? → answer
    ├── 다각도 분석? → parallel_search
    ├── 특정 URL 읽기? → fetch_page / fetch_bulk
    └── 사이트 차단? → stealthy_fetch (최후 수단)
```

---

## 🤖 21개 AI 에이전트 — 확장 메커니즘 매트릭스

한 번의 설정으로 모든 에이전트의 **확장 표면**에 리서치 우선 규칙을 주입합니다 — hooks, commands, plugins, cron, permissions 등.

| 에이전트 | MCP | Hooks | Commands | Agents/Cron/Plugins | 규칙 / 프롬프트 | Skills | 기타 표면 |
|-------|:---:|:-----:|:--------:|:-------------------:|-----------------|--------|-----------|
| **Claude Code** | ✅ | 4개 라이프사이클 훅 | `research.md` `verify.md` | — | `CLAUDE.md` + hooks | `~/.claude/skills/` nested | 권한 deny 패턴 |
| **Cursor** | ✅ | — | `research.json` `verify.json` | — | `.cursor/rules/*.md` | `~/.cursor/rules/` flat | `autoEnableTools` |
| **Kimi** | ✅ | `PreToolUse` (TOML) | — | — | `config.toml` `system_prompt` | `~/.kimi/skills/` nested | `default_yolo=false` |
| **Cline** | ✅ | `PreToolUse.py` | — | `maru-research-gate.md` 에이전트 + `.cron.md` | `.clinerules/*.md` | `~/.cline/skills/` flat | — |
| **Continue** | ✅ | — | `research` `verify` | — | `system_message` + `.continue/rules/` | `~/.continue/rules/` flat | — |
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
┌──────────────────────────────────────────────┐
│  maru-deep-pro-search MCP 서버               │
│  ├─ 10개 툴 (검색, 페치, 인용, 검증)         │
│  ├─ 9엔진 폴오버 레지스트리                  │
│  ├─ 하이브리드 랭킹 (BM25+시맨틱)            │
│  ├─ 3계층 강제 아키텍처                      │
│  ├─ 72시그니처 정제                          │
│  └─ SQLite 지식 저장소                       │
└──────────────────────────────────────────────┘
```

### 3계층 강제 아키텍처

1. **MCP 프롬프트 주입** — `always_research_first()` 프롬프트가 모든 툴 호출 전 `deep_research`를 강제
2. **세션 게이트** — `generate_code()`가 세션 내 리서치 없으면 코드 생성 차단
3. **에이전트 규칙** — 에이전트별 설정 파일(`.cursorrules`, `CLAUDE.md` 등)에 필수 리서치 프로토콜 주입

서버에 **생성형 LLM은 전혀 없습니다**. 종합은 규칙 기반이며, 에이전트의 LLM이 추론을 담당합니다. 선택적 시맨틱 점수는 임베딩 모델만 사용합니다.

기술적 심층 분석은 [`docs/engine_insights.md`](./docs/engine_insights.md)와 [`docs/lessons_learned.md`](./docs/lessons_learned.md)를 참조하세요.

### KnowledgeStore

SQLite 기반 연구 캐시 저장소 (`./.maru/knowledge.db`):

- **중복 제거** — 동일 쿼리는 `query_hash` 기준으로 UPSERT (access_count +1)
- **3단계 검색** — 정확히 일치 → FTS5 전문검색 → 시맨틱 유사도 (선택적, 로컬 `intfloat/multilingual-e5-small`)
- **도메인 통계** — 도메인별 성공률 및 평균 응답 시간 추적
- **정리(Prune)** — 30일 이상 된 오래된 캐시 엔트리 자동 삭제

`maru-deep-pro-search stats`로 확인합니다.

---

## 🔒 보안

가져온 콘텐츠는 72패턴 방어 계층을 통해 LLM에 도달하기 전에 정제됩니다:

- 제로폭 문자 제거 (`\u200b`, `\u200c`, `\u200d`)
- 채팅 토큰 중화 (`Human:`, `Assistant:` → `[REDACTED]`)
- MCP 특정 공격 탐지 (툴 포이즈닝, 럭 풀, 섀도잉)
- 선택적 시맨틱 유사도 이상 탐지

모든 툴 호출은 `.maru/audit.db`에 기록되며, 이상 징후 자동 탐지(급발사, 초대형 결과, 의심 파라미터)가 포함됩니다.

보안 정책은 [`SECURITY.md`](./SECURITY.md)를 참조하세요.

---

## ⚙️ 설정

모든 환경 변수는 선택사항입니다. `pydantic-settings`로 `MARU_SEARCH_` 접두사와 함께 로드됩니다.

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `ENGINE` | `duckduckgo_lite` | 기본 검색 엔진 |
| `MAX_RESULTS` | `10` | 엔진별 쿼리 결과 수 |
| `MAX_CONCURRENT` | `5` | 병렬 페치 제한 |
| `TIMEOUT` | `30.0` | 페치 타임아웃 (초) |
| `RETRIES` | `3` | 재시도 횟수 |

---

## 💻 CLI 명령어

```bash
# MCP 서버 (stdio 전송)
maru-deep-pro-search

# AI 에이전트 설정 + 스킬 파일 설치
maru-deep-pro-search setup
maru-deep-pro-search setup --list
maru-deep-pro-search setup --restore

# 프로젝트 하네스 초기화
maru-deep-pro-search init --agents cursor claude

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
# 가벼운 검색 모드 사용
MARU_SEARCH_MAX_RESULTS=5 maru-deep-pro-search
```

**내 에이전트에서 SKILL.md가 "미지원"으로 표시됨**
> 스킬 디렉토리 시스템이 없는 에이전트(예: Copilot, JetBrains)에서는 정상입니다. 규칙은 해당 에이전트의 기본 설정 파일을 통해 여전히 주입됩니다. 공식 스킬 지원이 있는 에이전트(Cursor, Kimi, Claude, Cline, Continue, Windsurf, Kilo, Tabnine, Hermes)에서만 스킬 설치가 표시됩니다.

---

## 🤝 기여하기

PR을 환영합니다. 개발 환경 설정, 엔진 추가, 에이전트 어댑터 추가 방법은 [`CONTRIBUTING.md`](./CONTRIBUTING.md)를 참조하세요.

---

## 📄 라이선스

MIT — [`LICENSE`](./LICENSE) 참조.
