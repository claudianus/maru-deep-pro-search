<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>AI 에이전트가 코딩 전에 반드시 리서치하도록.</strong><br>
  API 키 0개 · 9엔진 폴오버 · BM25+시맨틱 랭킹 · 네이티브 인용
</p>

<p align="center">
  <a href="./README.md">🇺🇸 English</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/test.yml?style=flat-square&label=tests" alt="Tests"></a>
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
| **엔진** | 1–2개, 폴오버 없음 | 9엔진 자동 폴오버 |
| **랭킹** | 엔진 기본 순서 | BM25 + 시맨틱 + 권위도/신선도/코드밀도 |
| **인용** | 환각 또는 없음 | `[1]`, `[2]` 네이티브 ID + 실제 URL |
| **방어** | 없음 | 72시그니처 프롬프트 인젝션 + 제로폭 문자 정제 |
| **강제** | "검색해주세요" (무시됨) | 3계층 기술적 게이트키핑 |
| **비용** | 변동 | **영원히 $0** — API 키 불필요 |

---

## 설치

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

## 빠른 시작

```python
from maru_deep_pro_search.tools import deep_research

result = deep_research(
    "Python pickle의 보안 위험은 무엇인가?"
)
print(result)  # 메타데이터가 포함된 랭킹된 URL 목록 — 에이전트가 fetch할 URL 결정
```

**MCP 툴 선택 가이드:**
- 빠른 답변? → `answer`
- 순위가 매겨진 소스 필요? → `web_search`
- 심층 분석? → `deep_research`
- 봇 차단 우회? → `stealthy_fetch`

에이전트별 설정은 [`AGENTS.md`](./AGENTS.md)를 참조하세요.

---

## 아키텍처

```
MCP 클라이언트 (Claude, Cursor, Kimi, Windsurf, ...)
        │ JSON-RPC 2.0 / stdio
        ▼
┌──────────────────────────────────────┐
│  maru-deep-pro-search MCP 서버       │
│  ├─ 8개 툴 (검색, 페치, 인용)       │
│  ├─ 9엔진 폴오버 레지스트리         │
│  ├─ 하이브리드 랭킹 (BM25+시맨틱)   │
│  ├─ 3계층 강제 아키텍처             │
│  └─ SQLite 지식 저장소              │
└──────────────────────────────────────┘
```

서버에 **생성형 LLM은 전혀 없습니다**. 종합은 규칙 기반이며, 에이전트의 LLM이 추론을 담당합니다. 선택적 시맨틱 점수는 임베딩 모델만 사용합니다.

기술적 심층 분석은 [`docs/engine_insights.md`](./docs/engine_insights.md)와 [`docs/lessons_learned.md`](./docs/lessons_learned.md)를 참조하세요.

---

## 8개 툴

| 툴 | 용도 |
|------|---------|
| `answer` | 인라인 인용이 포함된 빠른 답변 |
| `web_search` | 스크래핑 + 랭킹 + 인용된 결과 반환 |
| `search_with_citations` | 학술 작성용 사전 번호 소스 |
| `fetch_page` | 단일 URL에서 깨끗한 콘텐츠 추출 |
| `fetch_bulk` | 중복 제거가 포함된 병렬 페치 |
| `deep_research` | 갭 탐지가 포함된 전체 7단계 파이프라인 |
| `stealthy_fetch` | 보호된 사이트용 안티봇 우회 |
| `parallel_search` | 여러 검색을 동시에 실행 |

---

## 보안

가져온 콘텐츠는 72패턴 방어 계층을 통해 LLM에 도달하기 전에 정제됩니다:

- 제로폭 문자 제거 (`\u200b`, `\u200c`, `\u200d`)
- 채팅 토큰 중화 (`Human:`, `Assistant:` → `[REDACTED]`)
- MCP 특정 공격 탐지 (툴 포이즈닝, 럭 풀, 섀도잉)
- 선택적 시맨틱 유사도 이상 탐지

모든 툴 호출은 `.maru/audit.db`에 기록되며, 이상 탐지(급발사, 초대형 결과, 의심 파라미터)가 포함됩니다.

보안 정책은 [`SECURITY.md`](./SECURITY.md)를 참조하세요.

---

## 설정

모든 환경 변수는 선택사항입니다. `pydantic-settings`로 `MARU_SEARCH_` 접두사와 함께 로드됩니다.

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `ENGINE` | `duckduckgo_lite` | 기본 검색 엔진 |
| `MAX_RESULTS` | `10` | 엔진별 쿼리 결과 수 |
| `MAX_CONCURRENT` | `5` | 병렬 페치 제한 |
| `MAX_CONCURRENT` | `5` | 병렬 fetch 제한 |
| `TIMEOUT` | `30.0` | Fetch 타임아웃 (초) |
| `TIMEOUT` | `30.0` | 페치 타임아웃 (초) |
| `RETRIES` | `3` | 재시도 횟수 |

---

## Docker

```bash
# 빌드
docker build -t maru-search .

# stdio 전송으로 실행
docker run --rm -i maru-search

# 지속적인 지식 저장소와 함께 실행
docker run --rm -i -v $(pwd)/.maru:/app/.maru maru-search
```

---

## 문제 해결

**검색 엔진에서 결과가 없음**
```bash
MARU_SEARCH_ENGINE=bing maru-deep-pro-search
```

**설정 마법사가 에이전트를 감지하지 못함**
```bash
maru-deep-pro-search setup --agent cursor
maru-deep-pro-search setup --list-agents
```

**메모리 사용량 높음**
```bash
# 시맨틱 랭킹 비활성화
MARU_SEARCH_MAX_RESULTS=5 maru-deep-pro-search
```

---

## 기여하기

PR을 환영합니다. 개발 환경 설정, 엔진 추가, 에이전트 어댑터 추가 방법은 [`CONTRIBUTING.md`](./CONTRIBUTING.md)를 참조하세요.

---

## 라이선스

MIT — [`LICENSE`](./LICENSE) 참조.
