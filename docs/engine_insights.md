# Search Engine Insights & Optimization Guide

> Lessons learned from extensive scraping experiments with scrapling 0.2.99.

---

## 1. TextHandler Pitfalls

scrapling's ``TextHandler`` (returned by ``.text``) has a **broken ``__len__``** — ``len(el.text)`` often returns ``0`` even when text exists.

**Always use:**
```python
str(el.text)          # if el.text is not None
el.get_all_text()     # fallback for nested elements
```

The helper ``_text(el)`` in ``base.py`` encapsulates this safely.

---

## 2. Naver — Obfuscated DOM Recovery

Naver completely redesigned its SERP with hashed CSS classes (``sds-comps-*``, ``fender-ui_*``). Traditional selectors (``.total_wrap``, ``.lst_total``) return 0 matches.

**Solution:**
- Container: ``.fds-web-doc-root`` — reliably wraps each organic web result
- URL: ``a[nocr="1"]`` — **direct external links**, no redirect decoding needed
- Title/Snippet: ``get_all_text()`` parsing with UI noise filtering

Key insight: Naver still SSRs the core structure, so ``AsyncFetcher`` (no JS) is sufficient.

---

## 3. Baidu — Noise Filtering

Baidu mixes organic results with AI answers, ads, and recommendation widgets.

**Critical filter:** skip containers with class ``result-op`` (operational / promoted content).

Also filter internal URLs:
- ``nourl.ubs.baidu.com``
- ``recommend_list.baidu.com``
- ``baidu.php`` redirects

---

## 4. Google — Session Reuse is Everything

Google's rate limit is **not just IP-based**; it heavily weighs:
- Browser fingerprint consistency
- Cookie/session continuity
- Login state

**Key finding:** ``StealthyFetcher.async_fetch()`` launches a **fresh browser every call**, wiping all cookies. This triggers strict rate limits even with ``real_chrome=True``.

**Solution:** ``AsyncStealthySession`` reuses a single browser instance across requests. Cookies persist, and consecutive searches succeed without 429 errors.

Additional hardening:
- ``real_chrome=True`` — use system Chrome instead of bundled Chromium
- ``network_idle=True`` — wait for full page load
- ``block_webrtc=True``, ``hide_canvas=True`` — prevent IP/fingerprint leaks
- ``locale="en-US"``, ``timezone_id="America/New_York"`` — spoof US locale
- ``adaptive=True`` — recover if Google changes container selectors

---

## 5. Bing — Locale Parameters

Bing defaults to the user's IP geolocation. A Korean IP searching for "machine learning tutorial" returned Korean dictionary entries for "machine".

**Fix:** append ``setmkt=en-US&setlang=en`` to force English results.

---

## 6. DuckDuckGo — Region Locking

DuckDuckGo also geolocates. Append ``kl=us-en`` to prioritize US English results.

---

## 7. Startpage — Requires JS Rendering

Startpage proxies Google results but uses client-side JS to render them. ``AsyncFetcher`` returns empty results; ``StealthyFetcher`` (or ``AsyncStealthySession``) is mandatory.

---

## 8. Special Query Operators — Use with Caution

Automatic injection of ``site:``, ``filetype:``, etc. is **dangerous**:

| Operator | DuckDuckGo | Bing | Google | Verdict |
|----------|-----------|------|--------|---------|
| ``site:`` | ✅ Works | ❌ **0 results** | ❌ Bot detection | **Do NOT auto-inject** |
| ``filetype:`` | Untested | Untested | Untested | Risky for general search |

**Safer approach:** optimize **engine URL parameters** (``hl=``, ``setmkt=``, ``kl=``) instead of query operators.

---

## 9. URL Filtering — Global Improvements

Added to ``utils/url.py``:
- ``ubs.baidu.com`` — Baidu internal tracking
- ``recommend_list.baidu.com`` — Baidu recommendation widgets
- ``baidu.php`` — Baidu redirect proxy
- ``nourl.`` — Baidu placeholder URLs

---

## 10. Engine Architecture Decisions

### Avoid API-only engines
Brave (requires ``BRAVE_API_KEY``) and Academic (ArXiv + Semantic Scholar APIs) were removed. The project focuses on **direct HTML scraping** with no external API dependencies.

### Session vs Fetcher
| Pattern | Browser per call | Cookies persist | Rate limit risk |
|---------|-----------------|-----------------|-----------------|
| ``AsyncFetcher.get()`` | N/A (HTTP only) | N/A | Low |
| ``StealthyFetcher.async_fetch()`` | ✅ New every time | ❌ No | **High** |
| ``AsyncStealthySession`` | ❌ Reused | ✅ Yes | **Low** |

For any engine requiring JS rendering (Google, Startpage), prefer ``AsyncStealthySession``.
