# Lessons Learned — Search Engine Reliability & Rate Limiting

> Date: 2025-05-13  
> Context: maru-deep-pro-search v0.9.3 — comprehensive engine reliability overhaul  
> Tests: 202 passing

---

## Overview

This document captures the trial-and-error insights from a full-day reliability improvement session on the search engine layer. The focus was on **rate limiting**, **anti-bot evasion**, **obfuscated DOM handling**, and **scraping API ergonomics** with `scrapling>=0.2.99`.

---

## 1. scrapling 0.2.99 API Quirks

### 1.1 Timeout Units Are Inconsistent

| Class | Method | Timeout Unit |
|-------|--------|--------------|
| `AsyncFetcher` | `.get()` | **seconds** |
| `StealthyFetcher` | `.async_fetch()` | **milliseconds** |
| `AsyncStealthySession` | `.fetch()` | **milliseconds** |

**Lesson:** Always double-check timeout units when switching fetcher types. A `timeout=30` means 30s for `AsyncFetcher` but 30ms for stealth fetchers — the latter will always timeout immediately.

### 1.2 TextHandler Has a Broken `__len__`

scrapling's `TextHandler` (returned by `.text`) returns `len()==0` even when text exists.

**Safe patterns:**
```python
str(el.text)          # if el.text is not None
el.get_all_text()     # for nested elements
text.strip()          # after extraction
```

**Helper in `base.py`:** `_text(el)` encapsulates this safely.

### 1.3 Deprecation Warnings Are Cosmetic

scrapling internally calls `configure()` which emits `DeprecationWarning`. These are non-blocking and can be suppressed at the logging layer:
```python
logging.getLogger("scrapling").setLevel(logging.WARNING)
```

---

## 2. Rate Limit Architecture

### 2.1 Three-Layer Defense

We built a three-layer rate limit system:

```
┌─────────────────────────────────────────────┐
│  Layer 1: asyncio.Semaphore(3)              │  ← Global concurrency cap
│  (deep.py, tools.py)                        │     Prevents burst storms
├─────────────────────────────────────────────┤
│  Layer 2: EngineRateLimiter                 │  ← Per-engine cooldown
│  (__init_subclass__ wraps search())         │     Enforces min gap between
│                                             │     requests to same engine
├─────────────────────────────────────────────┤
│  Layer 3: TokenBucket (optional)            │  ← Global token rate limit
│  (utils/rate_limiter.py)                    │     For future fine-grained
│                                             │     QPS control
└─────────────────────────────────────────────┘
```

### 2.2 Engine Cooldowns Applied

| Engine | Cooldown | Rationale |
|--------|----------|-----------|
| Google | 3.0s | Most aggressive anti-bot |
| Startpage | 3.0s | Proxies Google, inherits limits |
| Baidu | 2.0s | Moderate blocking |
| Bing / Yahoo / Ecosia / Naver | 1.5s | Standard courtesy delay |
| DuckDuckGo | 1.0s | Most lenient |

**Implementation:** `SearchEngine.__init_subclass__` automatically wraps each subclass's `search()` method with `EngineRateLimiter.acquire()`. Subclasses only set `cooldown_seconds: float = X.X`.

### 2.3 Why Semaphore(3)?

Without concurrency limits, `deep_research()` spawns:
- 3–5 subquery tasks (primary engine)
- 3–8 secondary engine tasks

That's up to **13 simultaneous searches**. With Google's 429 sensitivity, this guarantees failure. `Semaphore(3)` caps simultaneous searches while still allowing parallelism across engines.

---

## 3. Google Anti-Bot: Session Reuse >> New Browser

### 3.1 The Core Discovery

Google's rate limit is **not purely IP-based**. It heavily weighs:
- Browser fingerprint consistency
- Cookie/session continuity
- Behavioral signals (navigation patterns)

`StealthyFetcher.async_fetch()` launches a **fresh browser per call**, wiping cookies and generating a new fingerprint each time. Even with `real_chrome=True`, consecutive calls trigger 429.

### 3.2 The Fix: AsyncStealthySession

`AsyncStealthySession` reuses a single browser context across requests. Cookies persist, fingerprint stays consistent, and consecutive searches succeed.

```python
self._session = AsyncStealthySession(
    real_chrome=True,       # Use system Chrome
    block_webrtc=True,      # Prevent IP leak via WebRTC
    hide_canvas=True,       # Prevent canvas fingerprinting
    network_idle=True,      # Wait for full page load
    timeout=60000,          # ms — generous for JS rendering
    google_search=True,     # Sets Google referer
)
```

### 3.3 Anti-Bot Detection

Google serves three types of block pages:
1. **CAPTCHA** (`sorry/index`) — Requires human intervention
2. **"Unusual traffic"** — Soft block, may resolve with backoff
3. **Empty results** — Hard block without explicit message

We detect #1 and #2 explicitly and raise `BlockedError` so the retry layer can fall back to other engines.

### 3.4 Adaptive Scraping

`page.css(selector, auto_save=True)` stores element properties on first hit. If Google changes its DOM, `page.css(selector, adaptive=True)` attempts recovery using stored heuristics.

**Limitation:** Adaptive scraping helps with **DOM changes**, not **bot detection**. If Google serves a block page, no selector recovery will help.

---

## 4. Naver: Obfuscated DOM Recovery

### 4.1 The Problem

Naver completely redesigned its SERP with hashed CSS classes:
- `sds-comps-*`
- `fender-ui_*`

Traditional selectors (`.total_wrap`, `.lst_total`) return 0 matches.

### 4.2 The Solution

| Element | Selector | Notes |
|---------|----------|-------|
| Container | `.fds-web-doc-root` | SSR-rendered, no JS needed |
| URL | `a[nocr="1"]` | Direct external links |
| Title | `.sds-comps-profile-info-title-text` | Still human-readable class |
| Snippet | `get_all_text()` parse | Filter UI noise ("Keep에 저장", "더보기") |

**Key insight:** Naver still SSRs core structure, so `AsyncFetcher` (no JS) is sufficient. The obfuscation targets bot farms that rely on stable class names, but SSR containers remain predictable.

### 4.3 Reliability Improvement

| Metric | Before | After |
|--------|--------|-------|
| Reliability score | 0.25 | 0.60 |
| Quality tier | 3 | 2 |
| Selector stability | Broken | Functional |

---

## 5. Baidu: Noise Filtering

### 5.1 The Problem

Baidu interleaves organic results with:
- AI-generated answers (`.result-op`)
- Sponsored content
- Recommendation widgets
- Internal tracking URLs

### 5.2 The Solution

**Container-level filter:**
```python
if "result-op" in (el.attrib.get("class") or ""):
    continue  # Skip AI/ads/recommendations
```

**URL-level filter** (added to `utils/url.py`):
- `nourl.ubs.baidu.com` — Placeholder/tracking
- `recommend_list.baidu.com` — Recommendation widgets
- `baidu.php` — Redirect proxy
- `nourl.` — Generic placeholder prefix

### 5.3 Consistency Fix

`rn=10` parameter ensures consistent result count. Without it, Baidu returns variable numbers of results depending on ad injection.

---

## 6. Bing: Locale Parameters

### 6.1 The Problem

Bing defaults to the user's IP geolocation. A Korean IP searching for "machine learning tutorial" returned:
- Korean dictionary entries for "machine"
- Korean Wikipedia disambiguation pages

### 6.2 The Fix

Append `setmkt=en-US&setlang=en` to force English results regardless of IP:
```python
f"https://www.bing.com/search?q={query}&count={n}&setmkt=en-US&setlang=en"
```

---

## 7. DuckDuckGo: Region Locking

DuckDuckGo also geolocates. Append `kl=us-en` to both HTML and Lite endpoints:
```python
f"https://html.duckduckgo.com/html/?q={query}&kl=us-en"
f"https://lite.duckduckgo.com/lite/?q={query}&kl=us-en"
```

---

## 8. Special Query Operators: Dangerous to Auto-Inject

We tested automatic injection of `site:`, `filetype:`, etc.:

| Operator | DuckDuckGo | Bing | Google | Verdict |
|----------|-----------|------|--------|---------|
| `site:` | ✅ Works | ❌ **0 results** | ❌ Bot detection | **Do NOT auto-inject** |
| `filetype:` | Untested | Untested | Untested | Risky |

**Safer approach:** Optimize **engine URL parameters** (`hl=`, `setmkt=`, `kl=`) instead of query operators. These are engine-native and don't trigger bot detection.

---

## 9. Startpage: JS Rendering Required

Startpage proxies Google results but uses client-side JS to render them. `AsyncFetcher` returns empty results; `AsyncStealthySession` is mandatory.

**Consistency fix:** Migrated Startpage from `StealthyFetcher` to `AsyncStealthySession` to match Google's architecture.

---

## 10. Code Deduplication to base.py

### 10.1 What Moved

Three helpers were duplicated across 8 engine files and moved to `base.py`:

| Helper | Purpose |
|--------|---------|
| `_first(el, selectors)` | Try multiple CSS selectors, return first match |
| `_text(el)` | Safe text extraction (TextHandler workaround) |
| `_guess_content_type(url, snippet)` | Classify result into ARTICLE/DOCUMENTATION/FORUM/CODE |

### 10.2 Refactored Engines

All 8 engine files now import from `base.py`:
- `duckduckgo.py`
- `google.py`
- `bing.py`
- `yahoo.py`
- `ecosia.py`
- `baidu.py`
- `startpage.py`
- `naver.py`

---

## 11. Engine Removal: API-Only Services

### 11.1 Removed

| Engine | Reason |
|--------|--------|
| **Brave** | Requires `BRAVE_API_KEY` — violates 100% free principle |
| **Academic** | Relies on ArXiv + Semantic Scholar APIs — not direct scraping |

### 11.2 Remaining Engines (9)

`duckduckgo`, `duckduckgo_lite`, `google`, `bing`, `yahoo`, `ecosia`, `baidu`, `startpage`, `naver`

---

## 12. Session vs Fetcher: Decision Matrix

| Pattern | JS Required | Cookies Persist | Rate Limit Risk | Best For |
|---------|------------|-----------------|-----------------|----------|
| `AsyncFetcher.get()` | ❌ No | N/A | Low | SSR pages (Naver, Bing, DDG) |
| `StealthyFetcher.async_fetch()` | ✅ Yes | ❌ No (new browser) | **High** | One-off stealth calls |
| `AsyncStealthySession.fetch()` | ✅ Yes | ✅ Yes | **Low** | Repeated stealth (Google, Startpage) |

**Rule of thumb:**
- If the engine serves SSR HTML → `AsyncFetcher`
- If JS rendering is needed AND you call it once → `StealthyFetcher`
- If JS rendering is needed AND you call it repeatedly → `AsyncStealthySession`

---

## 13. Architecture Patterns Established

### 13.1 Automatic Cooldown Wrapping

```python
class SearchEngine(ABC):
    cooldown_seconds: float = 0.0

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        original_search = cls.search
        @functools.wraps(original_search)
        async def _wrapped_search(self, *args, **kwargs):
            await limiter.acquire(self.name, self.cooldown_seconds)
            return await original_search(self, *args, **kwargs)
        cls.search = _wrapped_search
```

Subclasses just declare `cooldown_seconds = 3.0`. No manual wrapping needed.

### 13.2 Semaphore + Retry Composition

```python
_search_semaphore = asyncio.Semaphore(3)

async def _search_subquery(sq: str) -> list[SearchResult]:
    async with _search_semaphore:           # Layer 1: concurrency cap
        return await with_retry(            # Layer 2: retry logic
            primary_engine.search,
            sq,
            max_attempts=2,
            retryable_exceptions=(NetworkError, ParseError),
        )
        # Layer 3: cooldown enforced by __init_subclass__ wrapper
```

---

## 14. Remaining Known Issues

| Issue | Severity | Notes |
|-------|----------|-------|
| scrapling deprecation warnings | Low | Cosmetic, suppressible |
| Google 429 under heavy load | Medium | Session reuse mitigates but doesn't eliminate |
| Chrome profile collision | Medium | `user_data_dir` pointing to live Chrome fails when Chrome is running |
| Bing JS-rendered results | Low | Some Bing results now require JS; currently handled by HTML fallback |

---

## References

- `docs/engine_insights.md` — Companion doc with 10 focused insights
- `src/maru_deep_pro_search/engines/base.py` — Base class with cooldown wrapping
- `src/maru_deep_pro_search/utils/rate_limiter.py` — TokenBucket + EngineRateLimiter
- `src/maru_deep_pro_search/research/deep.py` — Semaphore usage in deep research
