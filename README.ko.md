<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>AI 에이전트가 코딩 전에 반드시 리서치하도록.</strong><br>
  API 키 0개 · 직접 스크래핑 · 인출 기반 · 시맨틱 하이브리드 랭킹 · 스마트 폴백
</p>

<p align="center">
  <a href="./README.md">🇺🇸 English</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/actions"><img src="https://img.shields.io/github/actions/workflow/status/claudianus/maru-deep-pro-search/publish.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/tests/"><img src="https://img.shields.io/badge/tests-193%20passing-brightgreen?style=flat-square" alt="Tests"></a>
  <a href="https://pypi.org/project/maru-deep-pro-search/"><img src="https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square" alt="Python"></a>
  <a href="https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://claudianus.github.io/maru-deep-pro-search/ko/">🌐 웹사이트</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## 한 줄 설치

> **요구사항:** Python **≥3.10** (설치 스크립트가 자동으로 맞춰줍니다)

**macOS / Linux — 권장 (uv 자동 설치):**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows (PowerShell) — 권장:**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**수동 설치 (pip):**
```bash
# Python 3.10 이상이 이미 설치되어 있어야 합니다
pip install maru-deep-pro-search[semantic] && maru-deep-pro-search setup
```

설정 마법사가 AI 에이전트(Claude Code, Cursor, Kimi, Windsurf 등)를 자동 감지하고, 기존 설정을 백업한 뒤 MCP 설정을 주입하고, 리서치 우선 규칙을 강제합니다. `[semantic]` extra는 `sentence-transformers>=3.0.0`을 설치하여 밀집 벡터 랭킹을 활성화합니다.

---

## 소개

AI 코딩 에이전트에는 치명적인 결함이 있습니다: 오래된 학습 데이터로 답변한다는 점입니다. `maru-deep-pro-search`는 에이전트에게 실시간 웹 검색 능력을 부여하고, **반드시 먼저 사용하도록 강제**합니다.

| 기능 | 구현 방식 |
|-----------|-----|
| **검색** | 7개 엔진을 비동기 HTTP로 직접 스크래핑. API 키 불필요. |
| **랭킹** | BM25 + 밀집 시맨틱 유사도 + 권위도/신선도/코드밀도 점수 |
| **리서치** | 쿼리 자동 확장, 스마트 페치, 갭 탐지를 포함한 7단계 딥 리서치 파이프라인 |
| **인출** | 모든 결과에 `[1]`, `[2]` ID 부여 — 네이티브 인출 아키텍처 |
| **강제** | 설정 CLI가 에이전트에 필수 리서치 우선 규칙을 주입 |
| **지속** | Harness 플랫폼이 프로젝트 지식을 SQLite에 저장 (선택적 시맨틱 임베딩) |

**핵심 원칙:** 영원히 100% 무상. OpenAI, Anthropic, Google Search API, SerpAPI, Bing API 없음. 오직 직접 스크래핑과 로컬 연산만 사용.

---

## 에이전트 내장 웹 검색만으로는 부족한 이유

최신 AI 코딩 에이전트들은 "웹 검색" 기능을 기본 탑재하고 있습니다. 편리해 보이지만, 실제로 의존필 때 문제가 드러납니다.

### 내장 웹 검색의 문제점

| 내장 웹 검색 | 실제 상황 |
|-------------|----------|
| **단일 엔진** | DuckDuckGo가 차단되면 끝입니다. 폴오버가 없습니다. |
| **정제 없는 결과** | 검색엔진이 뱉은 대로 전달합니다. 랭킹도, 품질 필터링도 없습니다. |
| **인용 부재** | 에이전트가 출처를 지어내거나 아예 무시합니다. |
| **얕은 페치** | 스니펫만 긁어 끝냅니다. 중요한 API 문서, 버전 표, 코드 예시를 놓칩니다. |
| **방어 없음** | 임의의 웹 페이지를 아묠 필터 없이 가져옵니다. 프롬프트 인젝션, 제로폭 문자, 악성 콘텐츠에 물방아가 없습니다. |
| **수동적** | 에이전트가 검색*할 수*는 있지만, 아무것도 강제하지 않습니다. 여전히 낡은 학습 데이터를 기본으로 사용합니다. |

### maru-deep-pro-search의 차이점

이건 검색 도구가 아닙니다. **리서치 강제 실행 플랫폼**입니다.

- **7엔진 자동 폴오버** — DuckDuckGo, Bing, Google, Naver, Qwant, Startpage, SearXNG. 하나가 망가지면 다음이 즉시 이어받습니다.
- **Perplexity급 랭킹** — BM25 관련성 + 시맨틱 유사도 + 권위도/신선도/코드밀도 점수. 최고의 소스가 정상에 오릅니다.
- **네이티브 인용** — 모든 주장에 `[1]`, `[2]`, `[3]`이 붙습니다. 출처는 실재하며 추적 가능하고 응답에 직접 포함됩니다.
- **딥 리서치 파이프라인** — 쿼리 자동 확장 → 다각도 검색 → 안티봇 에스컬레이션 스마트 페치 → 갭 탐지 → 인용된 종합 답변.
- **콘텐츠 품질 분석** — 코드 중심 페이지, API 문서, 낡은 콘텐츠, 권위 신호를 감지합니다. 무작위 블로그보다 공식 문서를 우선시합니다.
- **프롬프트 인젝션 방어** — 가져온 콘텐츠를 정제합니다: 제로폭 문자 제거, 채팅 토큰 중화, 의심 패턴 플래깅.
- **리서치 우선 강제** — 설정 CLI가 에이전트에 강제 규칙을 주입합니다: "어떤 코드를 작성하기 전에 반드시 deep_research를 호출하라." 예외 없음.
- **0 API 키** — 영원히 100% 물방아. OpenAI, Anthropic, SerpAPI, Bing API 불필요.

**결론:** 내장 검색은 에이전트에게 브라우저를 줍니다. `maru-deep-pro-search`는 에이전트에게 리서치 팀과 그들을 강제로 일하게 하는 최고 책임자를 줍니다.

---

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────────┐
│                         MCP 클라이언트 계층                           │
│                (Claude Code, Cursor, Kimi, Windsurf)                  │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ JSON-RPC 2.0 / stdio
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      maru-deep-pro-search                             │
│                          MCP 서버                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ 4개 프롬프트  │  │ 8개 도구     │  │ TOOL_GUIDANCE            │   │
│  │ (always_     │  │              │  │ (컨텍스트 수준 규칙)      │   │
│  │  research_   │  │              │  │                          │   │
│  │  first, ...) │  │              │  │                          │   │
│  └──────────────┘  └──────┬───────┘  └──────────────────────────┘   │
│                           │                                          │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       리서치 파이프라인                               │
│                                                                       │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐    │
│  │ 쿼리        │──▶│ 7개 엔진    │──▶│ 결과 병합 &             │    │
│  │ 확장기      │   │ (비동기)    │   │ 퍼지 중복 제거           │    │
│  │ (템플릿     │   │ 레지스트리  │   │ (자카드 + 시맨틱)        │    │
│  │ + 동의어)   │   │ 패턴)       │   │                         │    │
│  └─────────────┘   └─────────────┘   └───────────┬─────────────┘    │
│                                                  │                   │
│  ┌───────────────────────────────────────────────┘                   │
│  ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 하이브리드 랭킹 엔진                                          │   │
│  │  • BM25: k1=1.5, b=0.75 on 제목 + 요약 (rank-bm25)            │   │
│  │  • 메타데이터: 권위도 × 신선도 × 코드밀도                     │   │
│  │  • 시맨틱: cos_sim(쿼리, 텍스트) via multilingual-e5-small    │   │
│  │    (33M 파라미터, 384차원, 100+ 언어, MTEB 59.3)              │   │
│  │  • 최종: 엔진 신뢰도를 포함한 가중 앙상블                     │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┘                                        │
│  ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 스마트 페치 계층                                              │   │
│  │  • 네트워크 프로브 (DuckDuckGo RTT) → 적응형 타임아웃         │   │
│  │  • 도메인 이력 필터 (느림>5초 또는 실패>80% → 스킵)           │   │
│  │  • 우선순위 큐: 권위 도메인 먼저                              │   │
│  │  • 오류 유형 인지 전략:                                       │   │
│  │    DNS/네트워크 → 스킵 | SSL → 스텔스 재시도 | 403→스텔스    │   │
│  │  • Scrapling 세션 재사용 (AsyncDynamicSession 풀)             │   │
│  │    disable_resources=True, block_ads=True, 타임아웃 ms 단위   │   │
│  │  • 조기 중단: HIGH 품질 결과 3개 획득 시 중단                 │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┘                                        │
│  ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 콘텐츠 추출 파이프라인                                        │   │
│  │  • trafilatura: 본문 + 메타데이터 추출                        │   │
│  │  • htmldate: 발행일 탐지                                      │   │
│  │  • code.py: 21개 언어 구문 탐지, API 추출                     │   │
│  │  • sanitize.py: 제로폭 문자 제거, 챗 토큰                     │   │
│  │    중화, 의심 패턴 플래깅                                     │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┘                                        │
│  ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 종합 & 인출                                                   │   │
│  │  • 규칙 기반 종합 (서버에 LLM 없음)                           │   │
│  │  • 네이티브 [1], [2], [3] 인출 ID                             │   │
│  │  • 불완전 리서치에 대한 갭 탐지                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

서버에는 **생성형 LLM이 전혀 없습니다**. 종합은 규칙 기반으로 처리되며, 에이전트의 LLM이 추론을 담당합니다. 선택적 시맨틱 점수는 임베딩 모델(양방향 인코더만, 생성 없음)을 사용합니다.

---

## 8개 도구

| 도구 | 용도 | 사용 시기 |
|------|---------|-------------|
| `answer` | 인출이 포함된 빠른 답변 | 단순 사실 확인 |
| `web_search` | 스크래핑 + 랭킹 + 인출 결과 반환 | 순위가 매겨진 출처 필요 |
| `search_with_citations` | 학술/기술 문서용 사전 번호 출처 | 문서화, 논문 작성 |
| `fetch_page` | 단일 URL에서 깔끔한 콘텐츠 추출 | 알려진 출처 심층 분석 |
| `fetch_bulk` | 중복 제거를 포함한 병렬 페치 | 여러 알려진 URL |
| `deep_research` | 갭 탐지를 포함한 전체 7단계 파이프라인 | 복잡한 기술 질문 |
| `stealthy_fetch` | 보호된 사이트용 안티봇 우회 | Cloudflare 등 차단 시 |
| `parallel_search` | 여러 검색을 동시에 실행 | 비교 분석 |

**결정 트리:**
- 빠른 답변 필요? → `answer`
- 출처가 필요? → `web_search` 또는 `search_with_citations`
- 심층 분석? → `deep_research`
- 차단됨? → `stealthy_fetch`

---

## 기술 심층 분석

### 쿼리 확장 엔진

검색 엔진에 도달하기 전, 원본 쿼리는 템플릿 기반 시스템으로 확장됩니다:

- **템플릿**: `"{query} tutorial"`, `"{query} best practices"`, `"{query} documentation"`, `"{query} github"`, `"{query} vs alternative"`
- **동의어 주입**: 기술 용어는 일반적인 별칭으로 확장됨 (예: "docker compose" → "docker-compose")
- **언어 인식**: 한국어 쿼리는 한국어 전용 템플릿 사용 (예: `"{query} 사용법"`, `"{query} 예제"`)
- **출력**: 원본당 5–7개 확장 쿼리, 모든 엔진에서 병렬 실행

### 다중 엔진 검색 계층

7개 검색 엔진을 지원하며, 모두 직접 스크래핑 방식:

| 엔진 | 방식 | 페일오버 |
|--------|--------|----------|
| DuckDuckGo (lite) | HTML 스크래핑 | 기본 |
| DuckDuckGo (html) | HTML 스크래핑 | 폴백 |
| SearXNG | JSON API | 6개 인스턴스 라운드로빈 |
| Bing | HTML 스크래핑 | — |
| Google | HTML 스크래핑 + CAPTCHA 탐지 | — |
| Naver | 한국어 전용 HTML 스크래핑 | — |
| Qwant | 유럽 프라이버시 중심 | — |
| Startpage | 프라이버시 프록시를 통한 Google | — |

**레지스트리 패턴**: `SearchEngineRegistry`는 `_instances` 딕셔너리를 사용한 싱글턴 재사용이 있는 팩토리 패턴입니다. 모든 엔진이 동일한 `AsyncDynamicSession` 인스턴스를 공유하여 페치당 ~2초 브라우저 시작 오버헤드를 제거합니다.

**병렬 실행**: 모든 설정된 엔진에 대해 `asyncio.gather()`. 결과는 랭킹 전에 병합되고 중복 제거됩니다.

### 하이브리드 랭킹 알고리즘

랭킹 엔진은 4개 신호를 가중 앙상블로 결합합니다:

```
최종_점수 = bm25_점수    × 0.35
         + 권위도_점수   × 0.20
         + 신선도_점수   × 0.15
         + 코드밀도      × 0.10
         + 시맨틱_점수   × 0.20   (sentence-transformers 설치 시)
```

**BM25** (`rank-bm25`, k1=1.5, b=0.75): 제목 + 요약 말뭉치에서 계산. BM25는 역문서 빈도와 용어 빈도를 기반으로 문서를 점수화하는 확률적 검색 함수이며, 포화 및 길이 정규화를 포함합니다.

**권위도 점수**:
- 도메인 화이트리스트 보너스: `github.com`, `docs.python.org`, `developer.mozilla.org` 등은 +0.3
- TLD 점수: `.edu`, `.gov`, `.ac.kr`은 +0.2; `.blog`, `.medium`은 -0.1
- 경로 깊이 페널티: 깊은 경로(예: `/a/b/c/d`)는 약간 낮은 점수

**신선도 점수** (`htmldate`):
- HTML 메타데이터에서 발행일 추출
- 지수 감소: `점수 = exp(-days_old / 365)`
- 날짜 없는 페이지는 중립 점수(0.5)

**코드 밀도** (`pygments`):
- 언어에 맞는 렉서로 콘텐츠 토큰화
- `코드밀도 = 코드_토큰_수 / 전체_토큰_수`
- 기술 쿼리는 높은 코드 밀도 페이지를 부스트

**시맨틱 점수** (선택적, `sentence-transformers>=3.0.0`):
- 모델: `intfloat/multilingual-e5-small` (33M 파라미터, 384차원, 100+ 언어, MIT 라이선스, MTEB 59.3)
- 이 모델을 선택한 이유: `all-MiniLM-L6-v2`(영어만, 2021)을 한국어를 포함한 현대적 다국어 지원으로 대체
- 쿼리 임베딩과 페이지 텍스트 임베딩(처음 300자) 간 코사인 유사도
- 효율성을 위한 배치 처리
- **생성형 LLM이 아님**: 임베딩 전용 양방향 인코더. 사실적 추론 없음, 환각 위험 없음.
- 크로스 인코더는 평가 후 제거됨: 지연 시간 3배 증가에 비해 관련성 개선 <2%. 양방향 인코더 + BM25 하이브리드로 충분.

**중복 제거**:
- URL 수준 정확한 중복 제거 (`urllib.parse`로 정규화)
- 퍼지 중복 제거: 제목 + 요약에 대한 자카드 유사도 (임계값 0.72)
- 시맨틱 폴백 중복 제거: 코사인 유사도 >0.95로 근중복 탐지

### 스마트 페치 & 복원력

페치 계층은 프로덕션급 안정성을 위해 설계되었습니다:

**네트워크 프로브** (`_probe_network()`):
- 모든 `deep_research` 호출 시 DuckDuckGo RTT 측정
- 지연 시간에 따라 `timeout_per_fetch` 및 `max_sources` 조정
- 느린 네트워크(RTT >5초): 동시성 감소, 타임아웃 증가

**도메인 이력** (`KnowledgeStore.domain_stats`):
- SQLite 테이블이 `avg_duration_ms`, `failure_rate`, `last_updated`를 도메인별로 추적
- 느린 도메인(평균 >5초)은 선제적으로 스킵
- 신뢰할 수 없는 도메인(실패율 >80%)은 블랙리스트
- 모든 페치 시도 후 업데이트

**오류 유형 인지 처리**:

| 오류 | 전략 |
|-------|----------|
| DNS / 네트워크 연결 불가 | 즉시 도메인 스킵 |
| SSL 인증서 오류 | `AsyncStealthySession`으로 재시도 |
| HTTP 403 / 429 | 스텔스 + 동시성 감소로 재시도 |
| HTTP 404 | 스킵 |
| 타임아웃 | 타임아웃 +3초로 한 번 재시도 |
| CAPTCHA (Google 전용) | 플래그 지정 및 스킵 |

**Scrapling 최적화**:
- `disable_resources=True`, `block_ads=True`가 있는 `AsyncDynamicSession`
- `_get_session()`을 통한 세션 재사용 — 엔진 인스턴스당 단일 세션
- `timeout` 매개변수는 **밀리초** 단위 (`int(timeout * 1000)`으로 변환)
- 내장 재시도: `retries=2`, `retry_delay=1`

**조기 중단**:
- `max_concurrent=5`인 `asyncio.as_completed()`
- HIGH 품질 결과(trafilatura 추출 + content_length > 200) 3개 획득 시 중단
- `finally` 블록에서 적절한 Task 취소로 고아 코루틴 방지

### 콘텐츠 추출 파이프라인

```
원본 HTML
    │
    ▼
┌─────────────────┐
│ trafilatura     │ → 본문, 제목, 메타데이터
│ (주요 콘텐츠)   │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│htmldate│ │ code.py  │
│(날짜)  │ │(구문)    │
└────────┘ └──────────┘
    │         │
    ▼         ▼
┌─────────────────┐
│ sanitize.py     │ → LLM 주입용 안전
│ (방어 계층)     │
└─────────────────┘
```

**trafilatura**: HTML에서 주요 콘텐츠를 추출하고 탐색, 광고, 사이드바를 제거. 깔끔한 마크다운 형식 텍스트 반환.

**htmldate**: HTML 메타데이터, JSON-LD, 콘텐츠 분석에서 발행일을 발견하는 휴리스틱.

**code.py**: Pygments 렉서를 사용한 21개 언어 구문 탐지. API 시그니처, 함수 이름, 코드 블록을 코드밀도 점수용으로 추출.

**sanitize.py**: 프롬프트 인젝션 방어 계층:
- 제로폭 문자 제거 (`\u200b`, `\u200c`, `\u200d`, `\ufeff`)
- 챗 토큰 중화: `Human:`, `Assistant:`, `System:` 같은 시퀀스는 `[REDACTED]`로 대체
- 의심 패턴 탐지: 과도한 반복(>50%), base64 blob(>1KB), 유니코드 동형 문자
- 모든 살균은 LLM 컨텍스트 주입 **전에** 수행

### 시맨틱 검색 (선택적)

선택적 시맨틱 모듈은 생성 능력 없이 밀집 벡터 유사도를 추가합니다:

- **모델**: `intfloat/multilingual-e5-small`
  - 33M 파라미터, 384차원 임베딩
  - 한국어, 일본어, 중국어를 포함한 100+ 언어
  - MIT 라이선스(상업적 사용 가능)
  - MTEB 점수: 59.3 (all-MiniLM-L6-v2의 56.3 대비)
- **아키텍처**: 양방향 인코더 전용. 쿼리와 문서를 독립적으로 인코딩하고 유사도는 코사인 거리.
- **크로스 인코더 없음**: 평가 후 제거됨. 크로스 인코더는 관련성 개선 <2%에 ~800ms 지연 시간 추가. 양방향 인코더 + BM25 하이브리드로 충분.
- **지연 로딩**: `_LazyModels` 싱글턴을 통해 첫 사용 시 로드. CPU 전용.
- **우아한 저하**: `sentence-transformers`가 설치되지 않은 경우 모든 시맨틱 분기가 런타임 오류 없이 조용히 스킵.

설치: `pip install maru-deep-pro-search[semantic]`

### Harness 플랫폼

장기 실행 리서치 워크플로우를 위한 프로젝트 수준 지식 지속성:

**KnowledgeStore** (SQLite):
- `pages`: 전체 텍스트 검색(FTS5)이 있는 추출 콘텐츠
- `domain_stats`: 도메인별 성능 추적
- `semantic_embeddings`: 유사도 검색을 위한 선택적 벡터 저장
- `projects`: 프로젝트 메타데이터 및 구성

**WorkflowEngine** (7단계 생성기):
1. **프로브**: 네트워크 상태 확인
2. **확장**: 쿼리 확장
3. **검색**: 다중 엔진 병렬 검색
4. **랭킹**: 하이브리드 랭킹 + 중복 제거
5. **페치**: 도메인 필터링이 있는 스마트 페치
6. **추출**: 콘텐츠 추출 + 살균
7. **종합**: 규칙 기반 답변 + 인출 + 갭 탐지

**CLI 명령**:
```bash
maru-deep-pro-search init          # 현재 디렉토리에 .maru/ 초기화
maru-deep-pro-search setup         # AI 에이전트 통합 구성
```

### 인출 아키텍처

네이티브 인출 ID는 **종합 전에** 할당되어 모든 주장을 추적할 수 있도록 합니다:

1. 모든 엔진에서 검색 결과 수집
2. URL 중복 제거 + 퍼지 중복 제거
3. 하이브리드 랭킹이 최종 순서 생성
4. 최종 순위에 기반한 순차 ID `[1]`, `[2]`, `[3]` 할당
5. 종합이 이러한 안정적 ID를 참조
6. LLM이 사전 번호가 매겨진 출처를 받아 환각 인출 방지

`search_with_citations` 도구는 URL, 제목, 발행일이 있는 학술 형식으로 출처를 반환합니다.

---

## 성능 특성

| 지표 | 목표 | 구현 |
|--------|--------|----------------|
| 캐시 히트 (KnowledgeStore) | <100ms | SQLite FTS5 + 인덱스된 domain_stats |
| 전체 `deep_research` | <10초 | 7개 엔진, 5개 동시, HIGH 결과 3개 시 조기 중단 |
| Scrapling 세션 시작 | ~0ms (분할 상환) | 엔진 인스턴스당 단일 세션 재사용 |
| 시맨틱 모델 로드 | ~2초 (첫 호출만) | 지연 초기화, CPU 전용 |
| 메모리 사용량 | ~150MB 기본, +120MB 시맨틱 | GPU 불필요 |

---

## 설정 참조

모든 환경 변수는 선택 사항입니다. 런타임 구성은 `pydantic-settings`를 통해 `MARU_SEARCH_` 접두사로 로드됩니다.

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `MARU_SEARCH_ENGINE` | `duckduckgo_lite` | 기본 검색 엔진 |
| `MARU_SEARCH_MAX_RESULTS` | `10` | 엔진당 쿼리당 결과 수 |
| `MARU_SEARCH_MAX_CONCURRENT` | `5` | 병렬 페치 제한 |
| `MARU_SEARCH_MAX_TOKENS_SOURCE` | `2500` | 추출된 출처당 토큰 예산 |
| `MARU_SEARCH_MAX_TOKENS_TOTAL` | `20000` | 총 출력 토큰 예산 |
| `MARU_SEARCH_TIMEOUT` | `30.0` | 페치 타임아웃 (초) |
| `MARU_SEARCH_RETRIES` | `3` | 일시적 실패에 대한 재시도 횟수 |
| `MARU_SEARCH_STEALTH_TIMEOUT` | `15.0` | 스텔스 세션 타임아웃 (초) |
| `MARU_SEARCH_MIN_QUALITY_RESULTS` | `3` | HIGH 품질 결과에 대한 조기 중단 임계값 |

---

## 기존 방식 vs maru-deep-pro-search

| | 기존 방식 | maru-deep-pro-search |
|---|---|---|
| **에이전트 답변** | 오래된 2023년 학습 데이터 기반 | 신선도 점수가 있는 실시간 웹 검색 기반 |
| **출처** | 없음, 환각 가능성 | 실제 URL과 발행일이 있는 `[1]`, `[2]` |
| **설정** | 에이전트별 수동 MCP 설정 | 한 줄로 모든 에이전트 자동 감지 및 설정 |
| **비용** | 월 $5–50 API 비용 | **영구 물뢰** |
| **랭킹** | 원시 엔진 순서 | BM25 + 시맨틱 + 메타데이터 하이브리드 |
| **복원력** | 단일 장애점 | 7개 엔진 페일오버 + 스마트 폴백 |
| **지속성** | 상태 없음 | 프로젝트 수준 SQLite 지식 저장소 |

---

## 테스트

```bash
pytest tests/ -v
```

193개 테스트, 모두 통과. 모든 엔진, 랭킹 알고리즘, 콘텐츠 추출, 살균, Harness 지속성, 전체 리서치 파이프라인에 대한 통합 테스트를 포함한 단위 테스트를 커버합니다.

---

## 기여하기

PR 환영합니다. 코딩 스타일과 PR 가이드라인은 [CONTRIBUTING.md](./CONTRIBUTING.md)를 참조하세요.

릴리스 이력은 [CHANGELOG.md](./CHANGELOG.md)를 참조하세요.

---

## 라이선스

MIT © [claudianus](https://github.com/claudianus)
