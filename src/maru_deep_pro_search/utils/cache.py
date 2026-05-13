"""In-memory LRU cache for search results.

Zero external dependencies. Uses Python's built-in OrderedDict.
Cache entries expire after a configurable TTL to keep results fresh."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Simple TTL cache with LRU eviction.

    Args:
        maxsize: Maximum number of entries. Oldest accessed entries evicted first.
        ttl_seconds: Time-to-live in seconds. Entries expire after this duration.
    """

    def __init__(self, maxsize: int = 100, ttl_seconds: float = 300.0):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get value if present and not expired. Returns None if missing or stale."""
        now = time.monotonic()
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        if now > entry.expires_at:
            del self._cache[key]
            self._misses += 1
            return None
        # LRU: move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Store value with TTL."""
        now = time.monotonic()
        # Evict oldest if at capacity
        if len(self._cache) >= self.maxsize and key not in self._cache:
            self._cache.popitem(last=False)
        self._cache[key] = _CacheEntry(value=value, expires_at=now + self.ttl)
        self._cache.move_to_end(key)

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict[str, int | float]:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 3),
            "size": len(self._cache),
            "maxsize": self.maxsize,
        }


# Global cache instances (per-tool to avoid cross-contamination)
_search_cache = TTLCache(maxsize=200, ttl_seconds=300.0)  # 5 min TTL for search
_fetch_cache = TTLCache(maxsize=100, ttl_seconds=600.0)  # 10 min TTL for fetch


def get_search_cache() -> TTLCache:
    """Get the global search result cache."""
    return _search_cache


def get_fetch_cache() -> TTLCache:
    """Get the global fetch result cache."""
    return _fetch_cache


def cache_key(*parts: str) -> str:
    """Build a deterministic cache key from parts."""
    return "|".join(str(p) for p in parts)
