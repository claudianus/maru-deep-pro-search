# maru-deep-pro-search 로드맵

> **문서 언어:** 로드맵은 **한국어**로 유지합니다.

**현재:** PyPI [`0.19.1`](https://pypi.org/project/maru-deep-pro-search/) — **20개** 에이전트용 MCP 어댑터, **answer-engine** + **deep_research**, RRF·본문 랭킹·토큰/성능 최적화(0.18–0.19), 검색은 **영어(en) 전용**, 엔진은 **100% 무료** 스크래핑만.

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
- **설치 UX** — `setup` 전역 설정, 시맨틱 임베딩 기본 포함 (0.21+)
- **방어** — 프롬프트 인젝션 완화, 선택적 Docker, 감사용 SQLite

---

## 단기 (0.19.x)

| 우선순위 | 항목 | 메모 |
|----------|------|------|
| P0 | **품질 회귀 게이트** | 벤치 수동 실행 + CHANGELOG 하한선 (NDCG@10, P@5) |
| P1 | **harness.yaml merge** | `sync`가 프로젝트 harness를 실제 반영 |
| P1 | **Hermes 플러그인** | setup 시 버전 동기화 |
| P2 | **선택 LLM 요약** | opt-in만; 기본 비목표 유지 |

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
