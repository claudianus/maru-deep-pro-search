# maru-deep-pro-search

AI 에이전트가 코딩 및 분석 작업 전에 관련 최신 정보를 검색하여 컨텍스트에 주입할 수 있도록 돕는 MCP(Model Context Protocol) 서버입니다. 추가적인 API 키 설정 없이, 9개의 무료 검색 엔진 통합, RRF(Reciprocal Rank Fusion)와 BM25를 결합한 하이브리드 검색, 그리고 Granite 97M 모델을 통한 로컬 시맨틱 재랭킹(Semantic Re-ranking)을 지원합니다.

[🇺🇸 English](./README.en.md)

[![PyPI](https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue)](https://pypi.org/project/maru-deep-pro-search/)
[![Validate](https://github.com/claudianus/maru-deep-pro-search/actions/workflows/validate.yml/badge.svg)](https://github.com/claudianus/maru-deep-pro-search/actions/workflows/validate.yml)
[![Python](https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square)](https://pypi.org/project/maru-deep-pro-search/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square)](https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE)

[웹사이트](https://claudianus.github.io/maru-deep-pro-search/) · [프롬프트 템플릿](https://claudianus.github.io/maru-deep-pro-search/#prompts) · [PyPI 패키지](https://pypi.org/project/maru-deep-pro-search/) · [GitHub 저장소](https://github.com/claudianus/maru-deep-pro-search)

---

## 주요 특징

- **내장 경량 LLM 추론 엔진 (Refiner)**: `llama-cpp-python` 기반 Qwen3.5 모델(0.8B~4B)이 웹 콘텐츠를 자동으로 정제하여 광고/난비게이션을 제거하고 핵심 사실만 추출. 호스트 LLM의 토큰 사용량을 **83% 절약**합니다.
  - 하드웨어 자동 감지: RAM/VRAM/CPU/GPU 백엔드 자동 탐지 (NVIDIA CUDA, Apple Metal, ROCm, CPU)
  - 모델 자동 선택: VRAM > 6GB → 4B, VRAM > 2GB → 2B, else → 0.8B
  - GitHub Release 모델 미러링: 대용량 모델은 400MB chunk로 분할 다운로드 후 자동 병합
- **하이브리드 멀티 엔진 검색**: DuckDuckGo, Bing 등 9개 검색 소스를 연동하고 검색 실패 시 자동 페일오버(Failover)를 수행합니다.
- **시맨틱 재랭킹 (Semantic Re-ranking)**: 로컬에서 실행되는 `ibm-granite/granite-embedding-97m-multilingual-r2` 임베딩 모델을 활용하여 질의와 가장 연관성 높은 문서를 정교하게 추출합니다.
- **신뢰할 수 있는 인용 표기**: 환각을 최소화하기 위해 검색된 모든 정보 원본에 `[N]` 형식의 출처 태그 및 링크를 강제로 매핑합니다.
- **다양한 에이전트 연동**: Cursor, Claude Code, Cline, Aider 등 21종의 주요 AI 개발 도구를 지원합니다.
- **완전 묣료**: 상용 검색 API 키를 등록하지 않아도 모든 기능을 비용 없이 사용할 수 있습니다.
- **Perplexity-style 반복 리서치**: 호스트 에이전트가 `decompose` → `search` → `fetch` → `verify` 루프를 직접 제어하여 검색 품질 기준(정확도, 관련성)에 부합할 때까지 반복합니다.
## 핵심 도구 (MCP Tools)
| 도구 이름 | 주요 기능 |
| `search` | 웹 검색 + 낮은 refiner로 스니펫 정제 (relevance score, authority badge 포함) |
| `fetch` | 웹 페이지 본문 추출 + 낮은 refiner로 쓰레기 제거 (원본 6000tok → ~1000tok) |
| `fetch_bulk` | 여러 URL을 병렬로 fetch + 정제 |
| `verify` | 다중 출처 사실 교차 검증 및 충돌 감지 |
| `decompose` | 복잡한 질의를 서브쿼리로 분해 (의도/엔티티 추출) |

- **상세 도구 가이드**: [웹사이트 도구 소개](https://claudianus.github.io/maru-deep-pro-search/#tools) 참고
- **지원 에이전트 목록**: [웹사이트 에이전트 목록](https://claudianus.github.io/maru-deep-pro-search/#agents) 참고

---

## 설치 및 설정

### 1단계: 설치 스크립트 실행

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**Hatch / Pip를 이용한 수동 설치:**
```bash
> [!NOTE]
> 설치 스크립트가 시스템 하드웨어를 자동 탐지하고 최적의 Qwen3.5 모델(0.8B~4B)을 다운로드합니다. GPU(CUDA/Metal)가 있으면 가속 wheel을 자동으로 설치합니다.

pip install --user maru-deep-pro-search
maru-deep-pro-search setup
```

**uv를 사용하는 경우:**
```bash
uv tool install --python 3.12 maru-deep-pro-search
```

> [!NOTE]
> 시맨틱 재랭킹에 사용되는 Granite 97M 가중치 파일(Hugging Face)은 첫 실행 시 다운로드됩니다. 최초 검색 시의 콜드스타트 지연을 방지하기 위해 다음 명령어로 임베딩 모델을 미리 다운로드해 두는 것을 권장합니다.
> ```bash
> maru-deep-pro-search warmup-embeddings -q
> maru-deep-pro-search setup --check
> ```

### 2단계: 에이전트 설정

설치가 완료되면 에이전트(예: Cursor)를 **완전히 종료한 후 다시 실행**하십시오.

#### Claude Code 설정 (`~/.claude/settings.json`)
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

---

## 사용 방법

에이전트의 시스템 프롬프트(User Rules 등) 또는 첫 대화에 아래와 같은 지침을 지정하여 검색 활용을 강제할 수 있습니다.

- `"코드 작성 전에 반드시 웹 검색을 수행하여 최신 명세를 확인하고 [1], [2] 형식으로 명확한 출처를 표기해줘."`
- `"Next.js 15 App Router의 Server Action revalidate 에러 관련 최신 해결 방법을 검색해서 알려줘."`
- `"CVE-2026-40347 취약점 관련 공식 권고(Advisory)를 검색해 현재 프로젝트가 사용하는 버전이 안전한지 검증해줘."`

---

## 기능 비교

| 비교 항목 | maru | Tavily MCP | Perplexity MCP |
|:---|:---|:---|:---|
| **이용 비용** | **무료 ($0)** | 제한적 무료 / 유료 | 월 $5 이상 |
| **연동 엔진** | **9개 엔진 + 자동 페일오버** | 단일 API 제공 | 단일 API 제공 |
| **리서치 강제화** | **3단계 게이트 적용** | 지원 안 함 | 지원 안 함 |
| **리서치 모니터링** | **Trace 및 Insights 제공** | 지원 안 함 | 지원 안 함 |

---

## 품질 벤치마크

TREC(Text REtrieval Conference) 표준 데이터셋을 기준으로 한 검색 품질 측정 결과입니다. (10개 복합 쿼리 대상)

| 성능 지표 | 단일 엔진 기준 | 다중 엔진 (maru) |
|:---|:---|:---|
| **Precision@5** | baseline | **+86%** |
| **NDCG@10** | baseline | **+36%** |
| **MRR** | baseline | **+25%** |

*트레이드오프: 9개 엔진 통합 검색으로 인해 단일 엔진 대비 응답 시간이 약 2배 소요될 수 있습니다. (재현 명령어: `uv run python benchmark/search_quality_benchmark.py`)*

---

## 주요 환경 변수 설정

주요 동작을 제어하기 위해 시스템 환경 변수(Environment Variables)를 설정할 수 있습니다.

| 환경 변수 | 기본값 | 설명 |
|:---|:---|:---|
| `MARU_STRICT_QUERY` | `1` | 모호하거나 불완전한 검색어 입력을 필터링 및 정규화 |
| `MARU_EMBEDDING_MODEL` | Granite 97M R2 | 문서 재랭킹에 사용할 시맨틱 임베딩 모델 명세 |
| `MARU_BENCHMARK_SUITE` | — | `stress` 설정 시 부하 테스트 벤치마크 수행 |

- **전체 환경 변수 상세 설명**: [웹사이트 설정 페이지](https://claudianus.github.io/maru-deep-pro-search/#config) 참고

---

## 문제 해결 (Troubleshooting)

| 발생 현상 | 해결 방법 |
|:---|:---|
| MCP 서버가 에이전트에 노출되지 않음 | `maru-deep-pro-search setup`을 다시 실행한 뒤 에이전트 애플리케이션을 완전히 재시작합니다. |
| 첫 검색 실행 시 지나치게 느림 | `maru-deep-pro-search warmup-embeddings -q` 명령을 사전에 실행하여 가중치 파일을 캐시해 둡니다. |
| 설정 변경 사항이 반영되지 않음 | `maru-deep-pro-search update --with-setup` 또는 `setup --repair`를 실행해 에이전트 훅 설정을 초기화합니다. |
| 간헐적인 검색 엔진 에러 발생 | `engine_health` 도구를 통해 검색 소스의 실시간 헬스 상태를 점검합니다. |

---

## 기여 및 라이선스

- **기여 방법**: [CONTRIBUTING.md](CONTRIBUTING.md) 및 버그 리포트/PR 제출을 환영합니다.
- **라이선스**: 본 프로젝트는 MIT 라이선스에 따라 라이선스가 부여됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하십시오.
