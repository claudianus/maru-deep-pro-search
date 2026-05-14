"""URL normalization, filtering, and deduplication utilities."""

from __future__ import annotations

import base64
import re
from urllib.parse import unquote, urljoin, urlparse

# Domains that rarely contain useful text content
_SKIP_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "pinterest.com",
    "reddit.com",
    "linkedin.com",
    "snapchat.com",
    "twitch.tv",
    "ubs.baidu.com",
    "recommend_list.baidu.com",
}

# URL path patterns to skip
_SKIP_PATH_PATTERNS = [
    "/login",
    "/signup",
    "/register",
    "/auth",
    "/search",
    "/cart",
    "/checkout",
    "google.com/sorry",
    "google.com/recaptcha",
    "baidu.php",
    "nourl.",
]

# Tracking parameters to strip
_TRACKING_PARAMS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
]

# High-authority domains for coding agents
_AUTHORITY_DOMAINS = {
    "docs.python.org",
    "developer.mozilla.org",
    "mdn.io",
    "react.dev",
    "nextjs.org",
    "nodejs.org",
    "go.dev",
    "pkg.go.dev",
    "doc.rust-lang.org",
    "docs.rs",
    "api.rubyonrails.org",
    "learn.microsoft.com",
    "postgresql.org",
    "dev.mysql.com",
    "kubernetes.io",
    "fastapi.tiangolo.com",
    "docs.djangoproject.com",
    "vuejs.org",
    "svelte.dev",
    "github.com",
    "gitlab.com",
    "stackoverflow.com",
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com",
    "pypi.org",
    "npmjs.com",
    "crates.io",
    "realpython.com",
    "dev.to",
    "medium.com",
    # Korean developer communities
    "velog.io",
    "tistory.com",
    "naver.com",
    "daum.net",
    "brunch.co.kr",
    "okky.kr",
    "hashnode.dev",
}

# Primary / official source domains
_PRIMARY_SOURCE_DOMAINS = {
    "docs.python.org",
    "developer.mozilla.org",
    "mdn.io",
    "react.dev",
    "nextjs.org",
    "nodejs.org",
    "go.dev",
    "pkg.go.dev",
    "doc.rust-lang.org",
    "docs.rs",
    "api.rubyonrails.org",
    "guides.rubyonrails.org",
    "learn.microsoft.com",
    "docs.microsoft.com",
    "postgresql.org",
    "dev.mysql.com",
    "kubernetes.io",
    "helm.sh",
    "terraform.io",
    "fastapi.tiangolo.com",
    "flask.palletsprojects.com",
    "docs.djangoproject.com",
    "vuejs.org",
    "svelte.dev",
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "stackoverflow.com",
    "stackexchange.com",
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com",
    "pypi.org",
    "npmjs.com",
    "crates.io",
    "maven.apache.org",
    "rubygems.org",
    "packagist.org",
    "openai.com",
    "anthropic.com",
    "google.com",
    "cloud.google.com",
    "aws.amazon.com",
    "azure.microsoft.com",
}

# Official docs URL patterns
_DOCS_URL_PATTERNS = [
    "/docs/",
    "/documentation/",
    "/api/",
    "/reference/",
    "/guide/",
    "/manual/",
    "/spec/",
]

# Blog / review URL patterns
_BLOG_URL_PATTERNS = [
    "/blog/",
    "/news/",
    "/articles/",
    "/post/",
    "medium.com",
    "dev.to",
    "tistory.com",
    "velog.io",
    "brunch.co.kr",
    "hashnode.dev",
]

# Forum URL patterns
_FORUM_URL_PATTERNS = [
    "stackoverflow.com",
    "stackexchange.com",
    "reddit.com",
    "discourse.",
    "/forum/",
    "/community/",
    "/questions/",
    "okky.kr",
]

# Academic URL patterns
_ACADEMIC_URL_PATTERNS = [
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com",
    "doi.org",
    "ieee.org",
    "acm.org",
]

# News URL patterns
_NEWS_URL_PATTERNS = [
    "news.",
    "/news/",
    "techcrunch.com",
    "theverge.com",
    "hackernews",
    "hn.algolia.com",
]


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
    return any(domain == auth or domain.endswith("." + auth) for auth in _AUTHORITY_DOMAINS)


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
    """Resolve relative URLs and common redirect formats.

    Handles Google, DuckDuckGo, Bing, Yahoo, Baidu, and generic
    tracking redirect URLs to recover the canonical destination.
    """
    if not url:
        return ""

    # Google redirect: /url?q=TARGET or /url?sa=...&url=TARGET
    if url.startswith("/url?") or url.startswith("/search?"):
        for param in ["url", "q"]:
            m = re.search(rf"[?&]{param}=([^&]+)", url)
            if m:
                decoded = unquote(m.group(1))
                if decoded.startswith("http"):
                    return decoded
        # Sometimes Google wraps the URL twice
        m = re.search(r"[?&]url=([^&]+)", url)
        if m:
            inner = unquote(m.group(1))
            m2 = re.search(r"[?&]url=([^&]+)", inner)
            if m2:
                decoded = unquote(m2.group(1))
                if decoded.startswith("http"):
                    return decoded

    # DuckDuckGo redirect (multiple variants)
    if "duckduckgo.com/l/" in url or "r.duckduckgo.com/" in url:
        for param in ["uddg", "u", "url"]:
            m = re.search(rf"[?&]{param}=([^&]+)", url)
            if m:
                decoded = unquote(m.group(1))
                if decoded.startswith("http"):
                    return decoded

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

    # Baidu redirect
    if "baidu.com/link?" in url or "baidu.com/s?" in url:
        m = re.search(r"[?&]url=([^&]+)", url)
        if m:
            decoded = unquote(m.group(1))
            if decoded.startswith("http"):
                return decoded

    # Generic URL parameter redirect (e.g., ?url=..., ?redirect=..., ?target=...)
    if url.startswith("http") and "?" in url:
        for param in ["url", "redirect", "target", "dest", "href", "link", "goto"]:
            m = re.search(rf"[?&]{param}=([^&]+)", url)
            if m:
                decoded = unquote(m.group(1))
                if decoded.startswith("http") and len(decoded) > len(url):
                    return decoded

    # Relative URL
    if not url.startswith("http"):
        joined = urljoin(base_url, url)
        if joined.startswith("http"):
            return joined

    return url


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc.lower()


def classify_source_type(url: str, snippet: str = "") -> str:
    """Classify a URL into a SourceType category.

    Returns one of the SourceType enum values as a string.
    """
    from ..engines.base import SourceType

    lower_url = url.lower()
    domain = get_domain(url)
    combined = f"{lower_url} {snippet.lower()}"

    # GitHub / GitLab / BitBucket
    if any(d in domain for d in ["github.com", "gitlab.com", "bitbucket.org"]):
        return SourceType.GITHUB_REPO.value

    # Official docs
    if any(d in domain for d in _PRIMARY_SOURCE_DOMAINS):
        if any(p in lower_url for p in _DOCS_URL_PATTERNS):
            return SourceType.OFFICIAL_DOCS.value
        if domain in (
            "docs.python.org",
            "developer.mozilla.org",
            "mdn.io",
            "react.dev",
            "nextjs.org",
            "nodejs.org",
            "go.dev",
            "pkg.go.dev",
            "doc.rust-lang.org",
            "docs.rs",
            "learn.microsoft.com",
            "kubernetes.io",
            "fastapi.tiangolo.com",
            "docs.djangoproject.com",
            "vuejs.org",
            "svelte.dev",
        ):
            return SourceType.OFFICIAL_DOCS.value

    # Academic
    if any(p in lower_url for p in _ACADEMIC_URL_PATTERNS):
        return SourceType.ACADEMIC_PAPER.value

    # Package registry
    if any(
        d in domain
        for d in [
            "pypi.org",
            "npmjs.com",
            "crates.io",
            "rubygems.org",
            "packagist.org",
            "maven.apache.org",
        ]
    ):
        return SourceType.PACKAGE_REGISTRY.value

    # Forum
    if any(p in combined for p in _FORUM_URL_PATTERNS):
        return SourceType.FORUM.value

    # Tutorial
    if any(
        k in combined
        for k in [
            "tutorial",
            "getting started",
            "how to",
            "guide",
            "learn ",
            "lesson",
            "course",
            "walkthrough",
        ]
    ):
        return SourceType.TUTORIAL.value

    # News
    if any(p in lower_url for p in _NEWS_URL_PATTERNS):
        return SourceType.NEWS.value

    # Blog / review
    if any(p in lower_url for p in _BLOG_URL_PATTERNS):
        return SourceType.BLOG_REVIEW.value

    return SourceType.UNKNOWN.value


def is_primary_source(url: str, source_type: str = "") -> bool:
    """Return True if URL is from a primary/official source.

    Primary sources are authoritative: official docs, GitHub repos,
    package registries, academic papers, and Stack Overflow.
    """
    domain = get_domain(url)
    st = source_type.lower()

    if st in ("official_docs", "github_repo", "package_registry", "academic_paper"):
        return True

    if any(d in domain for d in _PRIMARY_SOURCE_DOMAINS):
        return True

    return "stackoverflow.com" in domain or "stackexchange.com" in domain


def resolve_canonical_url(url: str) -> str:
    """Best-effort canonical URL resolution.

    Strips tracking parameters, resolves redirects, and ensures
    the URL points to actual content rather than a redirector.
    """
    if not url or not url.startswith("http"):
        return url

    # First normalize
    url = normalize_url(url)

    # If it looks like a redirect URL, try to resolve it
    if "?" in url:
        for param in ["url", "q", "uddg", "u", "redirect", "target"]:
            m = re.search(rf"[?&]{param}=([^&]+)", url)
            if m:
                decoded = unquote(m.group(1))
                if decoded.startswith("http") and len(decoded) > 10:
                    return normalize_url(decoded)

    return url
