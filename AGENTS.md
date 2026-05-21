# 에이전트 지침 — maru-deep-pro-search

> **문서 언어:** 이 저장소의 **개발·기여 관련 문서는 한국어**를 기본으로 합니다. (영문 README: [`README.en.md`](README.en.md))

> **중요:** PyPI 배포는 **git 태그 push 시 자동**입니다. `twine`으로 수동 배포하지 마세요.

## 빠른 시작

```bash
uv sync --all-groups && source .venv/bin/activate

# 단일 파일 (빠른 피드백)
uv run ruff check src/maru_deep_pro_search/<파일>.py
uv run mypy src/maru_deep_pro_search/<파일>.py

# 전체 검증
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
```

**완료 조건(DoD)**
- [ ] `ruff check .` 통과
- [ ] `ruff format --check .` 통과
- [ ] `mypy src/` 통과 (오류 0개)
- [ ] `__version__`이 `pyproject.toml`과 일치
- [ ] `main`에 **직접 push 금지** — PR 사용

---

## 코드 스타일

- **ruff**: 줄 길이 100
- **import**: 파일 맨 위에 `from __future__ import annotations`
- **타입**: 전부 힌트; `Any`는 `# type: ignore[no-any-return]`와 함께만
- **이름**: 함수 `snake_case`, 클래스 `PascalCase`
- **독스트링**: 공개 API는 Google 스타일

## 낭비 방지 정책 (CTO 지시)

> **테스트는 전면 금지.** 테스트 파일·테스트 코드·픽스처·assert 없음.
>
> 테스트는 기술 부채입니다. 반복을 느리게 하고, 헛된 자신감을 주며, 잡는 버그보다 유지 비용이 큽니다. 올바른 검증은:
> 1. **정적 분석** — `ruff` + `mypy`가 실제 버그 대부분을 잡음
> 2. **런타임 강제** — 데코레이터(`_with_validation`, `_with_enforcement`)로 잘못된 입력이 로직에 들어가지 않게 함
> 3. **수동 검증** — 실제 입력으로 한 번 돌려보고 되면 배포
>
> 테스트를 쓰고 싶으면 타입 힌트를 보강하거나 검증기를 더 엄격하게 만드세요.

### 상속 안전 (필수)

**`__init__`을 재정의하는 모든 하위 클래스는 첫 줄에서 반드시 `super().__init__()`를 호출해야 합니다.**

```python
# 잘못됨
class XEngine(SearchEngine):
    def __init__(self):
        self.x = 1  # _circuit_breaker 등 부모 초기화 누락

# 올바름
class XEngine(SearchEngine):
    def __init__(self):
        super().__init__()  # 첫 줄
        self.x = 1
```

---

## 출력 형식 불변 조건

사용자가 명시적으로 허용하지 않는 한 깨뜨리지 마세요.
- `deep_research`: `## Research:`, `_engines:`, `quality:`, `### Sources`, `#### [N] Title`, `_score:`, `### Auto-Fetched Content` (`auto_fetch` > 0일 때)
- `web_search`: `Search:`, 번호 결과 `1. **Title** [N]`
- `fetch_page`: `EXTERNAL CONTENT`, `AGENT SECURITY PROTOCOL`
- `parallel_search`: `### Comparison Summary`, `| Query | Top Source | Type | Primary |`

---

## 피해야 할 것들 (함정)

| # | 함정 | 해결 |
|---|------|------|
| 1 | `__version__` ≠ `pyproject.toml` | 버전 올릴 때 **두 파일 모두** 확인 |
| 2 | PyPI 동일 버전 재업로드 | 새 버전으로 잘라야 함 (0.11.2 → 0.11.3) |
| 3 | cubic push 후 린트 깨짐 | cubic push **후마다** 전체 검증 |
| 4 | dependabot 요약만 읽음 | 기각 전 **전문** 확인 |
| 5 | `hasattr()` 남발 | dataclass 등 **명시적 계약** 사용 |
| 6 | `str(cache.get(key))` | `None` → `"None"`. `assert key is not None` 등 사용 |
| 7 | CI의 `\|\| true` | 실패를 삼킴. **완전히 제거** |
| 8 | 데드 코드 | 계산한 값이 실제로 쓰이는지 확인 |
| 9 | 플레이스홀더 없는 f-string | ruff F541. `f` 제거 |
| 10 | YAML front matter 들여쓰기 | `description: >`는 다음 줄 들여쓰기 필수 |
| 11 | 문자열 안 콜론 | front matter에서는 `'...'`로 따옴표 |
| 12 | 불변 조건 누락 | 출력 형식 바꾸면 **코드와 문서** 둘 다 |
| 13 | 오래된 dependabot PR | main 변경 후 머지 전 `@dependabot rebase` |
| 14 | `gh pr create` 본문에 백틱/파이프/`$` | bash가 해석함. `--body-file` 사용 |
| 15 | 머지 후 pull 안 함 | `git pull` 안 하면 로컬만 낡음 |
| 16 | PR 머지 가정 | 행동 전 `gh pr view N --json state` 확인 |
| 17 | Qwen3.5 모델 파일명 대소문자 | `Qwen3.5-0.8B-Q4_K_M.gguf` (대문자 Q). 소문자 `qwen3.5`로 다운로드 시 로드 실패 |
| 18 | GitHub Release 2GB 제한 | >2GB 모델은 400MB chunk로 분할 업로드 + `_merge_chunks()`로 병합 |
| 19 | Split chunk 순서 | `_download_chunks()`는 병합 전 `sorted()`로 chunk 순서 확인 필수 |
| 20 | Refiner 초기화 비용 | `llama-cpp-python` 첫 로드 수 초~수십 초. 캐시 재사용 필수 |

---

## 릴리스 절차

```bash
# 1. pyproject.toml과 __init__.py 둘 다 버전 수정
# 2. CHANGELOG.md + docs/index.html 뱃지
# 3. 전체 검증 → PR → cubic → merge
# 4. git checkout main && git pull
# 5. git tag vX.Y.Z && git push origin vX.Y.Z
# 6. gh run watch --workflow=publish.yml
```

---

## 코드 리뷰·머지 워크플로

```
1. git checkout -b feat/description
2. 작업 + 커밋
3. git push -u origin feat/description
4. gh pr create --title "feat: description" --body-file /tmp/pr.md
5. cubic 루프 (아래) — open 이슈 0건까지 반복
6. 머지 조건: CI 전체 통과 + cubic check pass + get_pr_issues open 0건
7. 머지 후 main pull → 태그 → publish.yml watch
```

### cubic 루프 (필수 — **코딩 에이전트가 직접** 수행)

**사용자에게 “cubic 돌려 주세요”로 넘기지 않는다.** PR을 열었거나 머지 직전이면 **에이전트**가 아래 루프를 끝까지 돌린 뒤 결과만 보고한다.

**`cubic · AI code reviewer`가 `pending`이거나 `get_pr_issues`에 open 이슈가 있으면 절대 머지하지 않는다.** pass 체크만으로는 부족하다.

```bash
# 1) cubic check가 pass 될 때까지 대기 (수 분 소요 가능)
gh pr checks <N> --watch  # 또는 60–120s 간격으로 gh pr checks <N> | rg cubic

# 2) open 이슈 조회 — MCP `get_pr_issues` (owner, repo, pullNumber)
# Open Issues > 0 이면 P1/P2부터 코드 수정 → commit → push → 1)부터 반복

# 3) Open Issues = 0 이고 CI 전체 pass 일 때만:
gh pr merge <N> --squash
```

- **담당:** 코딩 에이전트 — 대기·`get_pr_issues`·수정·push·재대기·(조건 충족 시) 머지까지.
- **반영:** 유효한 P1/P2는 코드로 고친다.
- **기각:** 오탐만 PR 코멘트에 근거를 남긴다 (코드 변경 없이 닫을 수 없으면 cubic에 회신).
- **재검:** push마다 cubic이 새 커밋을 리뷰할 때까지 다시 대기한다.
- **금지:** cubic pending / open 이슈 상태에서 “나중에 고침” 머지 · 사용자에게 cubic 루프만 안내하고 종료.

**PR 브랜치에 cubic push한 뒤에는 반드시:**
```bash
git pull origin <branch>
uv run ruff check src/ && uv run ruff format --check src/ && uv run mypy src/
```

---

## 벤치마크

```bash
# 검색 품질 벤치마크
uv run python benchmark/search_quality_benchmark.py

# Refiner 토큰 절약 벤치마크
uv run python benchmark/refiner_benchmark.py
```

다중 엔진 vs 단일 엔진 (TREC 표준, 10쿼리):
- Precision@5: **+86%** | NDCG@10: **+36%** | MRR: **+25%**
- 트레이드오프: 응답 시간 ~2배

Refiner 토큰 절약 (10개 테스트 URL):
- 평균 압축률: **83%** (6000tok → ~1000tok)
- 처리 속도: 0.8B 기준 ~50tok/s (Apple Metal M3), ~30tok/s (CPU)

---

## 실행으로 얻은 교훈

코드를 **읽은** 게 아니라 **돌려서** 알게 된 것들.

### 에이전트 행동 설계

1. **토큰 효율이 곧 강제** — 긴 문서는 무시된다. 한 줄 규칙은 지켜진다. SKILL.md ~50% 압축 + 한 줄 명령 13개.
2. **명령형 > 서술형** — "멈추고 즉시 검색"이 "불확실하면 검색을 고려"보다 잘 먹힌다.
3. **중간 트리거가 진짜 가치** — 에이전트는 한 번 검색하고 30분 코딩한다. 오류·리팩터·10–15분 자가 점검 트리거가 행동을 바꾼다.

### mypy 엄격 모드 (57 → 0 오류)

4. **`cache_key` 명시 캐스트** — `dict.get()`은 `str | None`. `str(cache.get(key))` 금지 — `None`이 `"None"`이 됨. `assert key is not None` 등.
5. **루프 변수 섀도잉** — 중첩 루프에서 이름 재사용하면 추론 깨짐.
6. **`__new__` 속성 접근** — dataclass `__new__`는 추적 우회. `# type: ignore[attr-defined]` 필요할 수 있음.
7. **`Exception` 포착이 너무 넓음** — `except Exception as e:`에서 `e`는 `Exception`. 세부 접근 전 서브클래스 단언.
8. **세션 재정의** — `if`/`else`에서 같은 변수에 다른 타입이면 첫 어노테이션을 명시.

### CI·자동화

9. **`\|\| true`는 실패 은닉** — `validate.yml`, `lint.yml`에서 발견. 신호 제거·시간만 소모.
10. **`gh pr create` 본문의 백틱/파이프/`$`** — bash 명령 치환. 항상 `--body-file`.
11. **cubic 리뷰는 오래된 커밋** — 체크 상태를 믿고, 코멘트 문구는 오래됐을 수 있음.
12. **품질 게이트 드리프트** — `mypy`/`ruff` 오류 증가 시 즉시 조사.
13. **dependabot PR 낡음** — main 바뀌었으면 머지 전 `@dependabot rebase`.

### 패키징·배포

14. **루트 파일은 pip에 안 들어감** — 패키지 디렉터리만 설치. `skills/`는 `src/maru_deep_pro_search/skills/` + `[tool.setuptools.package-data]`.
15. **YAML front matter 함정** — `description: >`는 들여쓰기, 문자열 속 콜론은 따옴표.
16. **플레이스홀더 없는 f-string** — ruff F541. `f` 제거.

### 테스트 제거 로그

| 날짜 | 파일 | 이유 | 제거된 테스트 수 |
|------|------|------|------------------|
| 2026-05-15 | `tests/test_documentation.py` | 독스트링 단어 검색은 실질 버그를 못 잡음 | 4 |
| 2026-05-15 | `tests/test_adapter_smoke.py` | 21개 어댑터에 걸친 105개 `isinstance(bool)`류; 실패 원인이 테스트 자체 | 105 |
| 2026-05-16 | **전체 테스트 파일** | CTO 지시: 테스트 금지. 정적 분석 + 런타임 강제 + 수동 검증만. | ~930 |

> **규칙:** 테스트 삭제는 긍정 신호다. 검토했고 가치 없다고 판단했다는 뜻이다. 제거는 모두 기록.

### 벤치마크·품질

17. **DuckDuckGo 서킷 브레이커 연쇄** — `asyncio.sleep(5)` 없이 연속 모드 전환 시 브레이커 오픈.
18. **단일 엔진이 이길 수 있음** — `deep_research`가 항상 이기는 건 아님. "httpx async" 등은 Bing 단일이 다중과 동급.
19. **그라운드 트루스 폭** — `nvd.nist.gov`만 보면 GitHub Advisory, Snyk 같은 정당 출처가 불이익.

---

## 아키텍처 결정

1. **100% 무료** — 유료 API 없음.
2. **엔진 레지스트리** — `SearchEngineRegistry`로 다중 엔진 페일오버.
3. **BM25 + 메타데이터** — Perplexity급 품질, 로컬 계산.
4. **인용 네이티브** — 외부 서비스 없이 `[1]`, `[2]` ID.
5. **리서치 퍼스트** — MCP 프롬프트 + `_with_enforcement`로 코딩 전 검색 강제.
6. **프롬프트 인젝션 방어** — 제로폭 제거, 채팅 토큰 중화.
7. **3층 레이트 리밋** — Semaphore(4) + 엔진별 쿨다운 + 슬라이딩 윈도우(`RateLimiter`).
8. **세션 재사용 스텔스** — Google/Startpage용 `AsyncStealthySession`.
9. **MCP 툴은 데이터만** — 종합은 에이전트 LLM이 결정.
10. **내장 Refiner 엔진** — `llama-cpp-python` 기반 Qwen3.5 경량 모델(0.8B~4B)이 웹 콘텐츠를 자동 정제. 호스트 LLM 토큰 83% 절약.
    - 하드웨어 자동 감지: RAM/VRAM/CPU/GPU 백엔드 (NVIDIA CUDA, Apple Metal, ROCm, CPU)
    - 모델 자동 선택: VRAM > 6GB → 4B, VRAM > 2GB → 2B, else → 0.8B
    - GitHub Release 모델 미러링: 2GB 제한 우회를 위해 400MB chunk로 분할 다운로드 후 자동 병합 (SHA256 검증)
11. **Atomic Tools v2** — Perplexity-style host-driven 반복 루프 (decompose → search → fetch → verify)
    - `search`: SERP + 낮은 refiner로 스니펫 정제 (호스트는 refiner 존재 모름)
    - `fetch`: 본문 + 낮은 refiner로 정제 (원본 6000tok → ~1000tok)
    - `verify`: 교차 검증 + 충돌 감지 + 신뢰도 점수
    - `decompose`: 쿼리 분해 (의도/엔티티/서브쿼리 생성)
