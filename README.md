<h1 align="center"><code>maru-deep-pro-search</code></h1>

<p align="center">
  <strong>AI 에이전트가 코딩 전에 반드시 리서치하도록.</strong><br>
  API 키 0개 · 9엔진 RRF+BM25+Granite 97M · Research Trace · 21개 에이전트
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
  <a href="https://claudianus.github.io/maru-deep-pro-search/#product-tour">📸 제품 투어</a> ·
  <a href="https://pypi.org/project/maru-deep-pro-search/">📦 PyPI</a> ·
  <a href="https://github.com/claudianus/maru-deep-pro-search">💻 GitHub</a>
</p>

---

## 소개

`maru-deep-pro-search`는 코딩 에이전트용 **MCP 하네스 + 딥리서치 슈퍼셋**입니다. 웹 조사 → Granite 시맨틱 재랭킹 → `[1]` 인용 패킷을 만들고, 규칙·세션·툴로 **코딩 전 검색**을 강제합니다.

| | 내장 검색 | maru-deep-pro-search |
|---|---|---|
| **엔진** | 1–2개 | **9 + 폴오버** |
| **랭킹** | 없음 | **RRF + BM25 + Granite 97M** |
| **인용** | 환각/없음 | **`[N]` + URL** |
| **딥리서치 UI** | 없음 | **Trace · Insights · Clusters** |
| **비용** | 변동 | **$0 · API 키 없음** |

상세 스크린샷·플레이북·18툴 표·ENV 전체: **[GitHub Pages](https://claudianus.github.io/maru-deep-pro-search/)**

---

## 3분 요약

1. **설치** → `maru-deep-pro-search setup` → 에이전트 재시작
2. **일반 질문** — *「갤럭시 S24 중고 시세」* → `answer`
3. **코드·보안·설계** — *「FastAPI vs Django 2026 architecture」* → `deep_research` (기본 30소스 · 7서브쿼리)
4. **업그레이드** — `pip install -U` 후 `update --with-setup` · `setup --check`

---

## ⚡ 10초 설치

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**수동:**
```bash
python3 -m pip install --user maru-deep-pro-search && maru-deep-pro-search setup
```

**Granite 97M (v0.22.1)** — 시맨틱 랭킹은 **항상 켜짐**. 기본 모델 `ibm-granite/granite-embedding-97m-multilingual-r2`. `install.sh` / `setup`이 `warmup-embeddings`로 Hugging Face 가중치를 **미리 받아** 첫 `deep_research` 콜드스타트를 줄입니다.

```bash
maru-deep-pro-search warmup-embeddings -q   # 수동 워밍
maru-deep-pro-search setup --check
```

**uv:**
```bash
uv tool install --python 3.12 maru-deep-pro-search
```

---

## 🚀 시작하기

```bash
maru-deep-pro-search --version   # 0.22.1
maru-deep-pro-search setup
```

업그레이드 시:
```bash
pip install -U maru-deep-pro-search
maru-deep-pro-search update --with-setup
maru-deep-pro-search setup --repair   # 훅·프로토콜 중복 시
maru-deep-pro-search setup --check
```

프로젝트 로컬 지식만:
```bash
maru-deep-pro-search init   # .maru/knowledge.db 등
```

Claude Code MCP 예시 (`~/.claude/settings.json`):
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

## 🏆 다른 도구와 비교

| 항목 | maru | Tavily MCP | Perplexity MCP |
|---|---|---|---|
| **비용** | **$0** | 무료 티어 / 유료 | $5+/월 |
| **엔진** | **9 + 폴오버** | API 1종 | API 1종 |
| **리서치 강제** | **3계층 게이트** | ❌ | ❌ |
| **딥리서치 UI** | **Trace·Insights** | ❌ | ❌ |

---

## 핵심 MCP 툴 (자주 쓰는 3개)

| 툴 | 용도 |
|------|------|
| `answer` | 일반 웹 질문 · 시세 · 추천 |
| `deep_research` | CVE, 아키텍처, 라이브러리 비교 (Trace·Insights·Clusters) |
| `fetch_page` | 공식 문서 URL 본문 (정제·인젝션 방어) |

**전체 18툴 · 선택 가이드:** [웹사이트 #tools](https://claudianus.github.io/maru-deep-pro-search/#tools)

**21 에이전트 어댑터 매트릭스:** [agent_matrix.html](https://claudianus.github.io/maru-deep-pro-search/agent_matrix.html)

---

## 📊 벤치마크 (TREC 스타일, 10쿼리)

| 지표 | 단일 엔진 | 다중 엔진 (maru) |
|------|-----------|------------------|
| Precision@5 | 기준 | **+86%** |
| NDCG@10 | 기준 | **+36%** |
| MRR | 기준 | **+25%** |

트레이드오프: 응답 시간 ~2배. 재현: `uv run python benchmark/search_quality_benchmark.py`

---

## 🔒 보안 (요약)

- 72패턴 프롬프트 인젝션 정제 + `fetch_page` EXTERNAL CONTENT 래핑
- `generate_code` — 세션 인용 없으면 코드 차단

상세: [웹사이트 #security](https://claudianus.github.io/maru-deep-pro-search/#security)

---

## ⚙️ 설정

자주 쓰는 ENV만:

| 변수 | 기본 | 설명 |
|------|------|------|
| `MARU_STRICT_QUERY` | `1` | 느슨한 쿼리 거절·정규화 |
| `MARU_EMBEDDING_MODEL` | Granite 97M R2 | 시맨틱 랭킹 모델 |
| `MARU_BENCHMARK_SUITE` | — | `stress`로 스트레스 벤치 |

**전체 ENV:** [웹사이트 #config](https://claudianus.github.io/maru-deep-pro-search/#config)

---

## 🐳 Docker

```bash
docker build -t maru-search .
docker run --rm -i -v $(pwd)/.maru:/app/.maru maru-search
```

---

## 변경 이력

**v0.22.0–0.22.1:** Granite 97M 필수 시맨틱 랭킹 · `warmup-embeddings` · Research Trace/Insights 품질 파이프라인.

전체: [CHANGELOG.md](CHANGELOG.md)

---

## 🆘 문제 해결

| 증상 | 조치 |
|------|------|
| MCP 안 보임 | `setup` 후 에이전트 재시작 |
| 첫 검색 느림 | `warmup-embeddings -q` |
| 설정 안 바뀜 | `update --with-setup` / `setup --repair` |
| 엔진 실패 | `engine_health` · 잠시 후 재시도 |

---

## 🤝 기여 · 라이선스

기여: [CONTRIBUTING.md](CONTRIBUTING.md) · 이슈/PR 환영.

MIT — [LICENSE](LICENSE)
