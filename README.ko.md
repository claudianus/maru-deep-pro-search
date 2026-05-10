<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>AI 에이전트가 코딩 전에 반드시 리서치하도록.</strong><br>
  API 키 0개 · 직접 스크래핑 · 인출 기반 답변
</p>

<p align="center">
  <a href="./README.md">🇺🇸 English</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/publish.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/tests/"><img src="https://img.shields.io/badge/tests-174%20passing-brightgreen?style=flat-square" alt="Tests"></a>
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-deep-pro-search/">🌐 웹사이트</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## 한 줄 설치

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

curl이 없으면:
```bash
pip install maru-deep-pro-search && maru-deep-pro-search setup
```

설정 마법사가 AI 에이전트(Claude Code, Cursor, Kimi, Windsurf 등)를 자동 감지하고, 기존 설정을 백업한 뒤, MCP 설정을 주입하고, 리서치 우선 규칙을 강제합니다.

---

## 소개

AI 코딩 에이전트에는 치명적인 결함이 있습니다: 오래된 학습 데이터로 답변한다는 점입니다. `maru-deep-pro-search`는 에이전트에게 실시간 웹 검색 능력을 부여하고, **반드시 먼저 사용하도록 강제**합니다.

| 기능 | 구현 방식 |
|-----------|-----|
| **검색** | 7개 엔진을 직접 스크래핑. API 키 불필요. |
| **랭킹** | BM25 + 권위도/신선도/코드밀도 점수 |
| **리서치** | 쿼리 자동 확장을 포함한 7단계 딥 리서치 파이프라인 |
| **인출** | 모든 결과에 `[1]`, `[2]` ID 부여 — 네이티브 인출 아키텍처 |
| **강제** | 설정 CLI가 에이전트에 필수 리서치 우선 규칙을 주입 |

**핵심 원칙:** 영원히 100% 무상. OpenAI, Anthropic, Google Search API, SerpAPI 없음.

---

## 8개 도구

| 도구 | 용도 |
|------|---------|
| `answer` | 인출이 포함된 빠른 답변 |
| `web_search` | 스크래핑 + 랭킹 + 인출 결과 반환 |
| `search_with_citations` | 학술/기술 문서용 사전 번호 출처 |
| `fetch_page` | 단일 URL에서 깔끔한 콘텐츠 추출 |
| `fetch_bulk` | 중복 제거를 포함한 병렬 페치 |
| `deep_research` | 7단계 파이프라인: 확장 → 검색 → 랭킹 → 크롤 → 종합 |
| `stealthy_fetch` | 보호된 사이트용 안티봇 우회 |
| `parallel_search` | 여러 검색을 동시에 실행 |

**결정 트리:**
- 빠른 답변 필요? → `answer`
- 출처가 필요? → `web_search` 또는 `search_with_citations`
- 심층 분석? → `deep_research`
- 차단됨? → `stealthy_fetch`

---

## 설정

모든 환경 변수는 선택 사항입니다:

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `MARU_SEARCH_ENGINE` | `duckduckgo_lite` | 기본 엔진 |
| `MARU_SEARCH_MAX_RESULTS` | `10` | 쿼리당 결과 수 |
| `MARU_SEARCH_MAX_CONCURRENT` | `5` | 병렬 페치 제한 |
| `MARU_SEARCH_MAX_TOKENS_SOURCE` | `2500` | 출처당 토큰 예산 |
| `MARU_SEARCH_MAX_TOKENS_TOTAL` | `20000` | 총 출력 토큰 예산 |
| `MARU_SEARCH_TIMEOUT` | `30.0` | 페치 타임아웃 (초) |
| `MARU_SEARCH_RETRIES` | `3` | 재시도 횟수 |

---

## 테스트

```bash
pytest tests/ -v
```

174개 테스트, 모두 통과.

---

## 라이선스

MIT © [claudianus](https://github.com/claudianus)
