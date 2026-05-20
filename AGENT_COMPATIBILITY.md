# 3-계층 강제 아키텍처 — 에이전트별 호환성 매트릭스

## 요약

| 에이전트 | Layer 1 서버 마킹 | Layer 2 클라이언트 훅 | 물리적 차단 강도 | 한계 / 주의사항 |
|---|---|---|---|---|
| **Claude Code** | O `answer` / `deep_research` 등으로 세션 마킹 | PreToolUse (Bash 차단) + PostToolUse (Write/Edit 사후 검증) + SessionStart (컨텍스트 주입) | **중간~강함** | PreToolUse 버그(GH#13744)로 Write/Edit은 exit 2가 차단 불가. SessionStart + PostToolUse 이중 보호로 우회 |
| **Aider** | O 리서치 툴 호출 시 세션 마킹 | lint-cmd + test-cmd 게이트 (14개 언어 자동 감지) | **강함** | 린트/테스트 실패 시 에디트 롤백. 가장 신뢰할 수 있는 물리적 차단 |
| **Cursor** | O 리서치 툴 호출 시 세션 마킹 | onPreEdit 훅 (2026+) — 편집 적용 전 veto + `.cursor/rules` + `/ask` `/search` `/compare` `/research` `/verify` | **중간~강함** | onPreEdit는 Cursor 2026+ 버전 필요. 구버전은 rules + defaultInstructions만 |
| **Hermes** | O 리서치 툴 호출 시 세션 마킹 | pre_tool_call 네이티브 플러그인 훅 + `/ask` `/search` `/compare` `/research` `/verify` | **강함** | 네이티브 훅이라 도구 호출 자체를 차단. 플러그인 설치 필요 |
| **Windsurf** | O 리서치 툴 호출 시 세션 마킹 | defaultInstructions + autoEnableTools | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Zed** | O 리서치 툴 호출 시 세션 마킹 | assistant.default_instructions | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Continue** | O 리서치 툴 호출 시 세션 마킹 | `/ask` `/search` `/compare` `/research` `/verify` 커스텀 커맨드 | **약함** | 커맨드는 편의성 제공. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **JetBrains** | O 리서치 툴 호출 시 세션 마킹 | mcp.autoEnableTools | **약함** | MCP 도구 자동 활성화. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Copilot** | O 리서치 툴 호출 시 세션 마킹 | defaultInstructions (VS Code settings.json) | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Cline** | O 리서치 툴 호출 시 세션 마킹 | defaultInstructions (VS Code settings.json) | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Devin** | O 리서치 툴 호출 시 세션 마킹 | devin.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Amazon Q** | O 리서치 툴 호출 시 세션 마킹 | amazonq.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Cody** | O 리서치 툴 호출 시 세션 마킹 | cody.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Codeium** | O 리서치 툴 호출 시 세션 마킹 | codeium.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Supermaven** | O 리서치 툴 호출 시 세션 마킹 | supermaven.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Tabnine** | O 리서치 툴 호출 시 세션 마킹 | tabnine.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **OpenCode** | O 리서치 툴 호출 시 세션 마킹 | opencode.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Kimi** | O 리서치 툴 호출 시 세션 마킹 | ~/.kimi/config 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Kilo** | O 리서치 툴 호출 시 세션 마킹 | kilo.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **AntiGravity** | O 리서치 툴 호출 시 세션 마킹 | antigravity.json 설정 주입 | **약함** | 프로토콜 주입만. 서버측 연구 게이트 + 클라이언트 규율에 의존 |
| **Codex** | O 리서치 툴 호출 시 세션 마킹 | `config.toml` + `AGENTS.md`, 선택적 `features.hooks` | **약함~중간** | 훅 활성화 시 일부 행동 제약 가능. 미설정 시 프로토콜 주입 수준 |

---

## Layer 1: Server-Side Session Marking

**`answer` 또는 `deep_research` 등 리서치 생산 툴** 호출 시 세션에 마킹됩니다. 이후 **미분류·코드 생성 의존 툴**은 유효한 연구 세션이 있어야 호출됩니다.

- **첫 진입(리서치 생산)**: `answer`, `deep_research`, `web_search`, `search_with_citations`, `parallel_search`, `fetch_page`, `fetch_bulk`, `stealthy_fetch` — 선행 리서치 없이 호출 가능하며 성공 시 세션 마킹
- **일반 웹 질문**: `answer(query, mode="balanced")` 권장 (시세·추천·한국어 소비자 검색)
- **코드·보안·깊은 조사**: `deep_research(query, auto_fetch=3)` 권장
- **면제(메타)**: `version`, `list_engines`, `engine_health`, `session_state`, `drift_status`, `query_knowledge`, `cache_stats`, `clear_caches`
- **`generate_code` / `export_research`**: 선행 리서치 + (generate_code) `research_id`·인용 `[N]` 검증
- 에이전트가 MCP를 우회하고 직접 파일 시스템에 쓰면 막을 수 없음

---

## Layer 2: Client-Side Hooks

### 물리적 차단 가능 (4개)

| 에이전트 | 훅 메커니즘 | 차단 시점 | 회피 난이도 |
|---|---|---|---|
| **Aider** | lint-cmd / test-cmd | 에디트 적용 후 린트/테스트 실행 시 | 거의 불가. 린트 실패=에디트 롤백 |
| **Hermes** | pre_tool_call 플러그인 | 도구 호출 직전 | 불가. 네이티브 훅이라 도구 실행 자체가 차단됨 |
| **Claude Code** | PreToolUse (exit 2) + PostToolUse + SessionStart | Bash: 실행 전 / Write/Edit: 사후 검증 | 중간. PreToolUse 버그로 Write/Edit은 SessionStart+PostToolUse로 이중 보호 |
| **Cursor** | onPreEdit (2026+) | 편집 적용 전 | 중간. 구버전 Cursor는 훅 미지원 |

### 프로토콜 주입만 (17개)

나머지 17개 에이전트는 설정 파일에 `RESEARCH_PROTOCOL`을 주입하는 것만 가능합니다. **MCP 호출 경로**에서는 Layer 1이 `generate_code` 등에 선행 리서치를 요구하고, 리서치 생산 툴은 첫 호출로 세션을 연다. 에이전트가 MCP를 우회해 직접 편집하면 막기 어렵습니다.

```
에이전트가 리서치 없이 generate_code 호출
    -> Layer 1: ResearchRequiredError (세션 미마킹 또는 만료)
에이전트가 answer / deep_research 로 세션 마킹
    -> 이후 generate_code 등 허용 (인용·research_id 검증)
에이전트가 IDE에서 직접 파일 편집 (MCP 우회)
    -> Layer 2 훅이 없으면 막기 어려움 → 훅 에이전트 권장
```

---

## Layer 3: Tool dependency (`generate_code`)

- **적용 대상**: MCP를 통해 `generate_code`를 호출하는 에이전트
- **메커니즘**: `generate_code(task_description, proposed_code, research_id, ...)` 호출 시
  1. 세션의 `research_id`와 일치하는가?
  2. `proposed_code`에 연구 산출물의 인용 `[N]`이 포함되어 있는가?
- **효과**: 에이전트가 “MCP citizen”으로 동작할 때 연구·코드 정합성을 강제
- **한계**: 에이전트가 툴을 호출하지 않고 직접 파일에 쓰면 무의미

**권장**: Layer 2 훅이 있는 에이전트(Claude Code, Aider, Cursor, Hermes)와 병행

---

## 종합 평가

| 강도 | 에이전트 |
|------|---------|
| **강함** | Aider, Hermes |
| **중간~강함** | Claude Code, Cursor (2026+) |
| **약함 (프로토콜 + Layer 1)** | 나머지 16개 — MCP 경로에서는 서버 게이트가 핵심 |

**실무 권장**: 코딩 에이전트는 **Claude Code / Cursor / Hermes / Aider** 중 하나 + `maru-deep-pro-search setup` 후 MCP 재시작.
