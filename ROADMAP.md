# maru-deep-pro-search 로드맵

> **문서 언어:** 로드맵은 **한국어**로 유지합니다.

**현재:** PyPI [`0.16.x`](https://pypi.org/project/maru-deep-pro-search/) — **20개** 에이전트용 MCP 어댑터, **answer-engine** + **deep_research**, 검색은 **영어(en) 전용**, 엔진은 **100% 무료** 스크래핑만.

**품질:** `ruff`·`mypy` 정적 분석과 런타임 검증/훅 — **자동 테스트 스위트 없음** (`AGENTS.md` 참고).

---

## 이미 반영된 것 (참고)

- **answer-engine** — `answer` 툴·스킬, 일반 웹 질문·시세·추천 진입점
- **다중 엔진 리서치** — `deep_research`, `parallel_search`, BM25 융합, 선택적 `auto_fetch`
- **MCP** — FastMCP 서버, stdio/HTTP, **18**개 툴 + 프롬프트 + 리소스
- **쿼리 게이트** — 자연어 → SERP 키워드 정규화, `MARU_STRICT_QUERY`로 거절 끄기 가능
- **스킬·훅** — `skills/` 패키지 동봉; 3계층 리서치 강제(서버 + 선택적 클라이언트 훅)
- **에이전트 어댑터** — `src/maru_deep_pro_search/cli/agents/`에 **20**개 Python 어댑터; `ask`/`search`/`compare` 커맨드(Claude, Cursor, Continue, Hermes)
- **Knowledge** — git 기반 문서 동기화용 `maru knowledge *` CLI
- **드리프트·영수증** — `drift_status`, `DeepResearchReceipt` (`deep_research` 경로)
- **설치 UX** — `setup` 전역 설정, `MARU_ENABLE_SEMANTIC_INSTALL` opt-in semantic
- **방어** — 프롬프트 인젝션 완화, 선택적 Docker, 감사용 SQLite

---

## 단기 (0.16.x–0.17)

| 우선순위 | 항목 | 메모 |
|----------|------|------|
| P0 | **영수증 다듬기** | `answer` 영수증, 툴 커버리지·오류 메시지 |
| P0 | **드리프트 UX** | 오탐 축소, `drift_status` 호출 시점 문서화 |
| P1 | **문서** | GitHub Pages·`AGENT_COMPATIBILITY` 지속 동기화, `docs/agent_matrix.html` |
| P1 | **어댑터 정리** | setup 시 커맨드·스킬 갱신 일관성 |
| P2 | **성능** | fetch 캐시·타임아웃, 엔진 헬스 |

---

## 중기

- **영수증·쿼리 게이트** — `generate_code`, 세션 상태 메시지와의 정합성
- **클라이언트 팩** — Continue 외 호스트용 스니펫
- **선택적 텔레메트리** — 필요 시 옵트인 유지보수 신호

---

## 비목표

- 기본 경로에 **유료 검색·유료 LLM API**
- 엔진의 **넓은 로캘 지원** (현재 정책상 영어 중심)
- **PyPI에 루트 전용 파일만 설치** — 패키지 데이터는 `src/maru_deep_pro_search/` 아래에만

---

## 기여

[`CONTRIBUTING.md`](CONTRIBUTING.md) 참고. `main`은 **브랜치 + PR**만 (브랜치 보호). 릴리스: `pyproject.toml` + `__init__.py` 버전, changelog, 태그 push → 자동 배포. **cubic 인라인 P1/P2는 머지 전 반영** (`AGENTS.md`).
