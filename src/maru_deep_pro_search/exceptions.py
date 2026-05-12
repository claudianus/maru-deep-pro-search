"""Structured exception hierarchy for maru-search."""

from __future__ import annotations


class MaruSearchError(Exception):
    """Base exception for all maru-search errors."""

    def __init__(
        self,
        message: str,
        retryable: bool = False,
        suggested_engine: str | None = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.suggested_engine = suggested_engine


class NetworkError(MaruSearchError):
    """Network-level failure (timeout, DNS, connection reset)."""

    def __init__(
        self,
        message: str,
        retryable: bool = True,
        suggested_engine: str | None = None,
    ):
        super().__init__(message, retryable=retryable, suggested_engine=suggested_engine)


class RateLimitError(MaruSearchError):
    """Rate limited by target site."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message, retryable=True)


class BlockedError(MaruSearchError):
    """Blocked by anti-bot or CAPTCHA."""

    def __init__(self, message: str, suggested_engine: str | None = None):
        super().__init__(
            message,
            retryable=True,
            suggested_engine=suggested_engine or "duckduckgo",
        )


class ParseError(MaruSearchError):
    """Failed to parse SERP or page content."""

    def __init__(
        self,
        message: str,
        retryable: bool = True,
        suggested_engine: str | None = None,
    ):
        super().__init__(
            message,
            retryable=retryable,
            suggested_engine=suggested_engine,
        )


class NoResultsError(MaruSearchError):
    """Query returned zero usable results."""

    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class ExtractionError(MaruSearchError):
    """Content extraction failed partially or fully."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message, retryable=retryable)
