"""URL normalization, filtering, and deduplication utilities."""

from __future__ import annotations

import base64
import re
from urllib.parse import unquote, urljoin, urlparse

# Domains that rarely contain useful text content
_SKIP_DOMAINS = {
    "youtube.com", "youtu.be", "instagram.com", "facebook.com",
    "twitter.com", "x.com", "tiktok.com", "pinterest.com",
    "reddit.com", "linkedin.com", "snapchat.com", "twitch.tv",
    "ubs.baidu.com", "recommend_list.baidu.com",
}

# URL path patterns to skip
_SKIP_PATH_PATTERNS = [
    "/login", "/signup", "/register", "/auth",
    "/search", "/cart", "/checkout",
    "google.com/sorry", "google.com/recaptcha",
    "baidu.php", "nourl.",
]

# Tracking parameters to strip
_TRACKING_PARAMS = [
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source",
]

# High-authority domains for coding agents
_AUTHORITY_DOMAINS = {
    "docs.python.org", "developer.mozilla.org", "mdn.io",
    "react.dev", "nextjs.org", "nodejs.org", "go.dev",
    "pkg.go.dev", "doc.rust-lang.org", "docs.rs",
    "api.rubyonrails.org", "learn.microsoft.com",
    "postgresql.org", "dev.mysql.com",
    "kubernetes.io", "fastapi.tiangolo.com",
    "docs.djangoproject.com", "vuejs.org", "svelte.dev",
    "github.com", "gitlab.com", "stackoverflow.com",
    "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com",
    "pypi.org", "npmjs.com", "crates.io", "realpython.com", "dev.to", "medium.com",
    # Korean developer communities
    "velog.io", "tistory.com", "naver.com", "daum.net",
    "brunch.co.kr", "okky.kr", "hashnode.dev",
}


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication.

    - Strip tracking parameters
    - Remove fragment
    - Normalize trailing slash
    """
    # Remove fragment
    if "#" in url:
        url = url.split("#", 1)[0]

    # Strip tracking parameters
    if "?" in url:
        base, query = url.split("?", 1)
        params = []
        for param in query.split("&"):
            if "=" in param:
                key = param.split("=", 1)[0]
                if key not in _TRACKING_PARAMS:
                    params.append(param)
        url = base + ("?" + "&".join(params) if params else "")

    return url.rstrip("/")


def should_skip_url(url: str) -> bool:
    """Return True if URL is unlikely to contain useful content."""
    lower = url.lower()

    # Skip social media and video sites
    domain = urlparse(url).netloc.lower()
    if any(d in domain for d in _SKIP_DOMAINS):
        return True

    # Skip common non-content paths
    if any(p in lower for p in _SKIP_PATH_PATTERNS):
        return True

    # Skip pure tracking URLs
    return bool(url.count("?") > 2 or url.count("&") > 5)


def is_authority_domain(url: str) -> bool:
    """Check if URL is from a known high-authority domain."""
    domain = urlparse(url).netloc.lower()
    return any(auth in domain for auth in _AUTHORITY_DOMAINS)


def deduplicate_urls(urls: list[str]) -> list[str]:
    """Remove duplicate URLs, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for u in urls:
        normalized = normalize_url(u)
        if normalized not in seen:
            seen.add(normalized)
            result.append(u)
    return result


def resolve_redirect(url: str, base_url: str) -> str:
    """Resolve relative URLs and common redirect formats."""
    # Google redirect
    if url.startswith("/url?") or url.startswith("/search?"):
        m = re.search(r"(?:url|q)=([^&]+)", url)
        if m:
            return unquote(m.group(1))

    # DuckDuckGo redirect
    if "duckduckgo.com/l/" in url and "uddg=" in url:
        m = re.search(r"uddg=([^&]+)", url)
        if m:
            return unquote(m.group(1))

    # Bing redirect (/ck/a?...&u=BASE64URL)
    if "/ck/a?" in url and "u=" in url:
        m = re.search(r"[?&]u=([^&]+)", url)
        if m:
            encoded = m.group(1)
            # Bing prefixes the payload with "a1" — strip it
            if encoded.startswith("a1"):
                encoded = encoded[2:]
            # Add base64 padding
            pad = 4 - len(encoded) % 4
            if pad != 4:
                encoded += "=" * pad
            try:
                decoded = base64.urlsafe_b64decode(encoded).decode("utf-8")
                if decoded.startswith("http"):
                    return decoded
            except Exception:
                pass

    # Yahoo redirect (r.search.yahoo.com/.../RU=URLENCODED)
    if "/r.search.yahoo.com/" in url and "/RU=" in url:
        m = re.search(r"/RU=([^/]+)", url)
        if m:
            decoded = unquote(m.group(1))
            if decoded.startswith("http"):
                return decoded

    # Relative URL
    if not url.startswith("http"):
        return urljoin(base_url, url)

    return url


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc.lower()
