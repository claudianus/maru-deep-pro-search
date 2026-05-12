"""Abstract base classes and data models for search engines."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from urllib.parse import urlparse

from ..utils.rate_limiter import CircuitBreaker
from ..exceptions import NetworkError

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    ARTICLE = "article"
    DOCUMENTATION = "docs"
    FORUM = "forum"
    CODE = "code"
    SPAM = "spam"
    UNKNOWN = "unknown"


class ExtractionQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EMPTY = "empty"
    BLOCKED = "blocked"


@dataclass
class SearchResult:
    """A single search result from any engine."""

    title: str
    url: str
    snippet: str = ""
    position: int = 0
    likely_content_type: ContentType = ContentType.UNKNOWN
    domain: str = ""
    url_suggests_docs: bool = False
    engine: str = ""
    # Citation support
    citation_id: int = 0
    # Cross-engine metadata
    engines_found: list[str] = field(default_factory=list)
    cross_engine_score: float = 0.0


@dataclass
class PageContent:
    """Extracted content from a fetched page."""

    url: str
    final_url: str = ""
    title: str = ""
    text: str = ""
    markdown: str = ""
    html: str = ""

    quality: ExtractionQuality = ExtractionQuality.EMPTY
    content_type: ContentType = ContentType.UNKNOWN
    content_length: int = 0
    heading_count: int = 0
    code_block_count: int = 0

    internal_links: list[dict] = field(default_factory=list)
    external_links: list[dict] = field(default_factory=list)
    needs_stealth: bool = False
    fetch_duration_ms: float = 0.0
    error_message: str = ""

    published_date: str = ""
    code_languages: list[str] = field(default_factory=list)
    api_signatures: list[dict] = field(default_factory=list)
    package_refs: list[dict] = field(default_factory=list)
    code_to_text_ratio: float = 0.0
    freshness_days: int | None = None
    is_api_reference: bool = False
    is_tutorial: bool = False
    is_error_solution: bool = False

    # Citation support for answer synthesis
    citation_id: int = 0


class SearchEngine(ABC):
    """Abstract base for all search engines.

    Subclasses should set quality metadata to help the registry
    recommend optimal engine combinations.

    Rate limiting:
        ``min_request_interval`` enforces a minimum delay between
        consecutive successful requests. Set it per-engine based on
        how strict the target site's rate limits are.

    Circuit breaker:
        Automatically stops sending requests to an engine after
        repeated failures, recovering after a cooldown period.

    Note:
        The ``search()`` method is automatically wrapped at class
        creation time to inject cooldown and circuit-breaker logic.
        Subclasses implement ``_do_search()`` instead.
    """

    name: str = ""
    supports_stealth: bool = False

    # Quality metadata (used by SearchEngineRegistry.recommend_engines)
    quality_tier: int = 2  # 1=best, 2=good, 3=fallback/last-resort
    typical_latency_ms: int = 1200
    reliability_score: float = 0.9  # 0.0-1.0, higher is more reliable

    # Rate limiting: minimum seconds between requests to this engine
    min_request_interval: float = 0.0

    def __init__(self):
        self._last_request_time: float = 0.0
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_seconds=60.0,
        )

    async def _ensure_cooldown(self) -> None:
        """Wait until ``min_request_interval`` has elapsed since the last request."""
        if self.min_request_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.min_request_interval:
            delay = self.min_request_interval - elapsed
            logger.debug(
                "[%s] Cooling down for %.2fs", self.name, delay
            )
            await asyncio.sleep(delay)
        self._last_request_time = time.monotonic()

    async def _check_circuit(self) -> bool:
        """Return True if the circuit breaker allows execution."""
        if not await self._circuit_breaker.can_execute():
            logger.warning(
                "[%s] Circuit breaker is OPEN; skipping request", self.name
            )
            return False
        return True

    def _record_success(self) -> None:
        """Record a successful request for circuit breaker tracking."""
        asyncio.create_task(self._circuit_breaker.record_success())

    def _record_failure(self) -> None:
        """Record a failed request for circuit breaker tracking."""
        asyncio.create_task(self._circuit_breaker.record_failure())

    def __init_subclass__(cls, **kwargs):
        """Wrap subclass ``search()`` with rate-limit + circuit-breaker logic."""
        super().__init_subclass__(**kwargs)
        original_search = cls.search

        @wraps(original_search)
        async def _wrapped_search(self, query: str, max_results: int = 10) -> list[SearchResult]:
            await self._ensure_cooldown()
            if not await self._check_circuit():
                raise NetworkError(
                    f"{self.name} circuit breaker is open",
                    retryable=False,
                    suggested_engine="duckduckgo_lite",
                )
            try:
                results = await original_search(self, query, max_results)
                self._record_success()
                return results
            except Exception as exc:
                self._record_failure()
                raise

        cls.search = _wrapped_search

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search and return results."""
        ...

    @abstractmethod
    async def fetch(self, url: str, stealth: bool = False, timeout: float = 15.0) -> PageContent:
        """Fetch and extract content from a URL.

        Args:
            url: Target URL.
            stealth: Use anti-bot bypass.
            timeout: Max seconds for the fetch operation (converted to ms for Scrapling).
        """
        ...


# ── Shared extraction utilities ─────────────────────────────────────────────

def _first(el, selectors: list[str]):
    """Try multiple CSS selectors and return the first match."""
    for sel in selectors:
        results = el.css(sel)
        if results:
            return results[0]
    return None


def _text(el) -> str:
    """Safely extract text from a scrapling element.

    scrapling's ``TextHandler`` can return ``None`` for ``.text``
    on nested elements. This helper falls back to ``get_all_text()``.
    """
    if el is None:
        return ""
    if el.text is not None:
        return str(el.text).strip()
    return el.get_all_text().strip() if hasattr(el, "get_all_text") else ""


def _guess_content_type(url: str, snippet: str = "") -> ContentType:
    """Guess content type from URL and snippet text."""
    lower = (url + " " + snippet).lower()
    domain = urlparse(url).netloc.lower()

    # Korean-specific detection
    korean_indicators = [
        "velog.io", "tistory.com", "naver.com/blog",
        "brunch.co.kr", "okky.kr",
    ]
    if any(ind in domain for ind in korean_indicators):
        if domain.endswith("github.com"):
            return ContentType.CODE
        return ContentType.ARTICLE

    if any(k in lower for k in ["github.com", "gitlab.com", "bitbucket.org"]):
        return ContentType.CODE
    if any(k in lower for k in ["stackoverflow.com", "stackexchange.com", "discourse", "forum"]):
        return ContentType.FORUM
    if any(k in lower for k in ["docs.", "/docs/", "documentation", "reference", "api.", "/api/"]):
        return ContentType.DOCUMENTATION
    if any(k in lower for k in ["medium.com", "dev.to", "blog.", "/blog/", "tistory.com", "velog.io", "brunch.co.kr"]):
        return ContentType.ARTICLE
    return ContentType.UNKNOWN
