"""Content extraction utilities: URL filtering, deduplication, token-efficient truncation.

Note: link extraction is handled by the engine's _collect_links during fetch_page,
exposed via PageContent.internal_links / PageContent.external_links."""

import re
from urllib.parse import urlparse


def truncate_for_llm(text: str, max_tokens_approx: int = 2000) -> str:
    """Truncate text to roughly max_tokens_approx (4 chars ≈ 1 token), at a clean boundary."""
    max_chars = max_tokens_approx * 4
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]

    # Try paragraph boundary
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.5:
        return truncated[:last_para].strip()

    # Try sentence boundary
    last_sent = max(
        truncated.rfind(". "),
        truncated.rfind(".\n"),
        truncated.rfind("! "),
        truncated.rfind("? "),
    )
    if last_sent > max_chars * 0.5:
        return truncated[:last_sent + 1].strip()

    # Word boundary
    return truncated.rsplit(" ", 1)[0].strip() + "..."


def skip_url(url: str) -> bool:
    """Skip URLs that are unlikely to contain useful content."""
    skip_patterns = [
        "youtube.com/watch", "youtu.be/",
        "instagram.com/p/", "twitter.com/", "x.com/",
        "facebook.com/", "tiktok.com/",
        "/login", "/signup", "/register", "/auth",
        "apple.com/app", "play.google.com",
        "pinterest.com", "reddit.com/r/",
    ]
    lower = url.lower()
    return any(p in lower for p in skip_patterns)


def deduplicate_urls(urls: list[str]) -> list[str]:
    """Remove duplicate URLs, normalizing trailing slashes."""
    seen: set[str] = set()
    result: list[str] = []
    for u in urls:
        normalized = u.rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            result.append(u)
    return result
