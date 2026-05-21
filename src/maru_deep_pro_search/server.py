from __future__ import annotations

import functools
import ipaddress
import logging
import os
import socket
import sys
import time
from importlib.metadata import version as get_version
from urllib.parse import urlparse

from mcp.server.fastmcp import Context, FastMCP

from maru_deep_pro_search.engines.registry import SearchEngineRegistry
from maru_deep_pro_search.tools_v2 import (
    tool_decompose,
    tool_fetch,
    tool_fetch_bulk,
    tool_search,
    tool_verify,
)

mcp = FastMCP("maru-deep-pro-search-v2")

_logger = logging.getLogger("maru_deep_pro_search.server_v2")
if os.environ.get("MARU_DEBUG") in ("1", "true", "yes"):
    _logger.setLevel(logging.DEBUG)
else:
    _logger.setLevel(logging.WARNING)

for _noisy in (
    "mcp",
    "mcp.server",
    "sentence_transformers",
    "scrapling",
    "scrapling.fetchers",
    "transformers",
    "huggingface_hub",
    "httpx",
):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
_logger.addHandler(_stderr_handler)
_logger.propagate = False


# ── Helpers ──────────────────────────────────────────────────


def _is_private_host(hostname: str | None) -> bool:
    """Return True if hostname resolves to a private/loopback/internal IP."""
    if hostname is None:
        return True
    lower = hostname.lower()
    if lower in ("localhost", "localhost.localdomain"):
        return True
    if lower.endswith((".local", ".internal", ".lan")):
        return True
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        pass
    try:
        addr = ipaddress.ip_address(int(hostname))
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except (ValueError, OverflowError):
        pass
    try:
        packed = socket.inet_aton(hostname)
        addr = ipaddress.ip_address(socket.inet_ntoa(packed))
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except (OSError, ValueError):
        pass
    return False


def _get_session_id(ctx: Context | None) -> str:
    """Extract a stable session identifier from the MCP context."""
    if ctx is None:
        return "unknown"
    client_id = getattr(ctx, "client_id", None)
    if client_id:
        return f"client:{client_id}"
    try:
        session = getattr(ctx, "session", None)
        if session is not None:
            return f"session:{id(session)}"
    except Exception:
        pass
    try:
        request_context = getattr(ctx, "request_context", None)
        session = getattr(request_context, "session", None)
        if session is not None:
            return f"session:{id(session)}"
    except Exception:
        pass
    return f"request:{getattr(ctx, 'request_id', 'unknown')}"


# ── Decorators ───────────────────────────────────────────────

_SESSIONS: dict[str, dict] = {}


def _with_enforcement(tool_name: str | None = None):
    """Decorator that enforces research-first behavior per session."""

    def decorator(fn):
        name = tool_name or fn.__name__

        @functools.wraps(fn)
        async def wrapper(*args, ctx: Context | None = None, **kwargs):
            session_id = _get_session_id(ctx)
            state = _SESSIONS.setdefault(session_id, {"research_done": False, "tools": []})

            if name in {"search", "fetch", "fetch_bulk"}:
                result = await fn(*args, ctx=ctx, **kwargs)
                state["research_done"] = True
                state["tools"].append(name)
                return result

            if not state["research_done"]:
                notice = (
                    "⚠️  Research-first notice: No research has been performed in this session. "
                    "Call `search()` or `fetch()` before using dependent tools.\n\n"
                )
                result = await fn(*args, ctx=ctx, **kwargs)
                if isinstance(result, str):
                    return notice + result
                return result

            result = await fn(*args, ctx=ctx, **kwargs)
            state["tools"].append(name)
            return result

        return wrapper

    return decorator


def _with_validation(tool_name: str | None = None):
    """Decorator that validates MCP tool input parameters to prevent DoS."""

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, ctx: Context | None = None, **kwargs):
            if "query" in kwargs:
                q = kwargs["query"]
                if isinstance(q, str):
                    if not q.strip() and (tool_name or fn.__name__) != "fetch_bulk":
                        raise ValueError("Query cannot be empty or whitespace-only.")
                    if len(q) > 4096:
                        raise ValueError(
                            f"Query exceeds maximum length of 4096 characters (got {len(q)})"
                        )
            if "urls" in kwargs:
                urls = kwargs["urls"]
                if isinstance(urls, list):
                    if len(urls) > 50:
                        raise ValueError(f"Maximum 50 URLs allowed per call (got {len(urls)})")
                    if any(not isinstance(u, str) or not u.strip() for u in urls):
                        raise ValueError("All URLs must be non-empty strings.")
            if "max_tokens" in kwargs:
                mt = kwargs["max_tokens"]
                if isinstance(mt, int) and (mt < 100 or mt > 32000):
                    raise ValueError(f"max_tokens must be between 100 and 32000 (got {mt})")
            if "max_results" in kwargs:
                mr = kwargs["max_results"]
                if isinstance(mr, int) and (mr < 1 or mr > 100):
                    raise ValueError(f"max_results must be between 1 and 100 (got {mr})")
            if "mode" in kwargs:
                mode = kwargs["mode"]
                if isinstance(mode, str) and mode not in ("fast", "balanced", "deep", "standard"):
                    raise ValueError(
                        f"mode must be one of 'fast', 'balanced', 'deep', or 'standard' "
                        f"(got {mode!r})"
                    )
            for url_key in ("url", "urls"):
                if url_key in kwargs:
                    urls = kwargs[url_key]
                    to_check = urls if isinstance(urls, list) else [urls]
                    for u in to_check:
                        if not isinstance(u, str):
                            continue
                        if not u.startswith(("http://", "https://")):
                            raise ValueError(
                                f"URL must use http:// or https:// scheme (got: {u[:60]})"
                            )
                        parsed = urlparse(u)
                        if parsed.hostname is None:
                            raise ValueError(f"Invalid URL (no hostname): {u[:60]}")
                        if _is_private_host(parsed.hostname):
                            raise ValueError(
                                "URL points to internal/private address "
                                f"(SSRF protection): {u[:60]}"
                            )
            return await fn(*args, ctx=ctx, **kwargs)

        return wrapper

    return decorator


def _with_audit(tool_name: str | None = None):
    """Decorator that logs every MCP tool invocation to the audit database."""

    def decorator(fn):
        name = tool_name or fn.__name__

        @functools.wraps(fn)
        async def wrapper(*args, ctx: Context | None = None, **kwargs):
            from maru_deep_pro_search.harness.audit import AuditLogger

            start = time.perf_counter()
            params = {k: v for k, v in kwargs.items() if k != "ctx"}
            try:
                result = await fn(*args, ctx=ctx, **kwargs)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                AuditLogger().log_tool_call(
                    tool_name=name,
                    parameters=params,
                    result_preview=f"ERROR: {exc}",
                    session_id=_get_session_id(ctx),
                    duration_ms=duration_ms,
                )
                raise

            duration_ms = (time.perf_counter() - start) * 1000
            AuditLogger().log_tool_call(
                tool_name=name,
                parameters=params,
                result_preview=str(result)[:500] if result else "",
                session_id=_get_session_id(ctx),
                duration_ms=duration_ms,
            )
            return result

        return wrapper

    return decorator


# ── Core tools ───────────────────────────────────────────────


@mcp.tool()
@_with_enforcement("search")
@_with_validation("search")
@_with_audit("search")
async def search(
    query: str,
    engine: str = "auto",
    max_results: int = 10,
    ctx: Context | None = None,
) -> str:
    """Search the web and return structured, token-efficient results."""
    return await tool_search(query, engine, max_results)


@mcp.tool()
@_with_validation("fetch")
@_with_audit("fetch")
async def fetch(
    url: str,
    max_tokens: int = 6000,
    ctx: Context | None = None,
) -> str:
    """Fetch and refine web page content."""
    return await tool_fetch(url, max_tokens)


@mcp.tool()
@_with_validation("fetch_bulk")
@_with_audit("fetch_bulk")
async def fetch_bulk(
    urls: list[str],
    max_concurrent: int = 5,
    max_tokens: int = 3000,
    query: str = "",
    ctx: Context | None = None,
) -> str:
    """Parallel fetch multiple known URLs with deduplication."""
    return await tool_fetch_bulk(urls, max_concurrent, max_tokens, query)


@mcp.tool()
@_with_validation("verify")
@_with_audit("verify")
async def verify(
    sources: list[dict],
    ctx: Context | None = None,
) -> str:
    """Cross-verify facts across multiple sources."""
    return await tool_verify(sources)


@mcp.tool()
@_with_validation("decompose")
@_with_audit("decompose")
async def decompose(
    query: str,
    mode: str = "standard",
    ctx: Context | None = None,
) -> str:
    """Decompose a complex query into sub-queries for iterative research."""
    return await tool_decompose(query, mode)


# ── Utility tools ────────────────────────────────────────────


@mcp.tool()
@_with_validation()
@_with_audit("version")
async def version(ctx: Context | None = None) -> str:
    """Return the current version of maru-deep-pro-search."""
    try:
        ver = get_version("maru-deep-pro-search")
    except Exception:
        from maru_deep_pro_search import __version__

        ver = __version__
    return f"maru-deep-pro-search v{ver}"


@mcp.tool()
@_with_validation()
@_with_audit("list_engines")
async def list_engines(ctx: Context | None = None) -> str:
    """List all available search engines with their metadata."""
    lines = ["## Available Search Engines", ""]
    for name in SearchEngineRegistry.list_engines():
        try:
            cls = SearchEngineRegistry.get(name)
            status = (
                "🟢"
                if cls.reliability_score >= 0.85
                else "🟡"
                if cls.reliability_score >= 0.7
                else "🔴"
            )
            lines.append(
                f"{status} **{name}** — tier {cls.quality_tier}, "
                f"reliability {cls.reliability_score:.0%}, "
                f"~{cls.typical_latency_ms}ms"
            )
        except Exception:
            lines.append(f"⚪ **{name}** — metadata unavailable")
    lines.append("")
    lines.append("Tip: Use `engine_health()` to check real-time circuit breaker status.")
    return "\n".join(lines)


@mcp.tool()
@_with_validation()
@_with_audit("engine_health")
async def engine_health(
    engine: str = "",
    ctx: Context | None = None,
) -> str:
    """Check the health status of search engines."""
    engines_to_check = [engine] if engine else SearchEngineRegistry.list_engines()
    lines = ["## Engine Health Status", ""]

    for name in engines_to_check:
        try:
            eng = SearchEngineRegistry.create(name)
            cb = eng._circuit_breaker
            cb_state = (
                "CLOSED ✅"
                if cb.state == "closed"
                else "OPEN ❌"
                if cb.state == "open"
                else "HALF-OPEN ⚠️"
            )
            lines.append(
                f"**{name}**: {cb_state} | "
                f"failures: {cb.failure_count}/{cb.failure_threshold} | "
                f"cooldown: {eng.min_request_interval}s"
            )
        except Exception as exc:
            lines.append(f"**{name}**: ERROR — {exc}")

    return "\n".join(lines)


# ── Entry point ──────────────────────────────────────────────


def run() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
