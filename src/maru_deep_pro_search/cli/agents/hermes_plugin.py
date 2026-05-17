"""Hermes plugin — real research enforcement via pre_tool_call hook.

This plugin is distributed as part of maru-deep-pro-search and is
auto-discovered by Hermes via the ``hermes_agent.plugins`` entry point.
It provides:

- ``pre_tool_call`` hook that blocks un-researched tool usage
- ``post_tool_call`` hook for audit logging
- ``/research`` slash command for manual research triggering
- ``/verify`` slash command for session verification

Usage
-----
1. Install maru-deep-pro-search (this pulls in the plugin automatically) ::

       pip install maru-deep-pro-search

2. Enable the plugin in Hermes ::

       hermes plugins enable maru-research-gate

3. The hook now guards every tool call.  Run ``/research <query>`` before
   any other tool, or the gate will reject the call with an explanatory
   message.
"""

from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════
# Research gate state — filesystem-backed session tracking
# ═══════════════════════════════════════════════════════════════════════

SESSION_FILE = Path.home() / ".maru" / "session_research.json"
SESSION_TTL_MINUTES = int(os.environ.get("MARU_RESEARCH_TTL", "30"))


def _check_research() -> tuple[bool, str]:
    """Return (ok: bool, message: str)."""
    if not SESSION_FILE.exists():
        return False, "No research session found. Run /research <query> first."

    try:
        data = json.loads(SESSION_FILE.read_text())
    except Exception:
        return False, "Corrupted session research file."

    completed_at = data.get("completed_at")
    if not completed_at:
        return False, "Research not marked as completed."

    try:
        ts = datetime.fromisoformat(completed_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        return False, f"Invalid timestamp: {completed_at}"

    now = datetime.now(timezone.utc)
    if now - ts > timedelta(minutes=SESSION_TTL_MINUTES):
        return (
            False,
            f"Research expired (TTL={SESSION_TTL_MINUTES}min). Re-run /research.",
        )

    rid = data.get("research_id", "")
    if not rid.startswith("RSCH-"):
        return False, f"Invalid research_id format: {rid}"

    return True, f"Research {rid} valid."


# ═══════════════════════════════════════════════════════════════════════
# Plugin entry point — called by Hermes on startup
# ═══════════════════════════════════════════════════════════════════════


def register(ctx) -> None:
    """Register hooks and commands with Hermes.

    Called automatically by Hermes when the plugin is enabled.
    The ``ctx`` object provides the Hermes plugin context API.
    """

    # ── Hook: pre_tool_call ─────────────────────────────────────────
    def on_pre_tool_call(tool_name: str, params: dict, **kwargs) -> dict | None:
        """Block any tool call before deep_research has been done.

        Returning ``{"action": "block", "reason": "..."}`` aborts the
        tool execution and sends the reason back to the model.
        """
        # deep_research itself is exempt — it *is* the research step
        if tool_name == "deep_research":
            return None

        ok, msg = _check_research()
        if not ok:
            return {
                "action": "block",
                "reason": (
                    f"[MARU-RESEARCH-GATE] BLOCKED '{tool_name}': {msg} "
                    f"Run /research <query> to unlock."
                ),
            }

        # Also gate code-generation-like tools extra strictly
        gated_suffixes = ("write", "edit", "create", "modify", "generate")
        if any(s in tool_name.lower() for s in gated_suffixes):
            rid = json.loads(SESSION_FILE.read_text()).get("research_id", "")
            ctx.inject_message(
                f"[MARU-GATE] Tool '{tool_name}' executed under research {rid}.",
                role="system",
            )

        return None

    ctx.register_hook("pre_tool_call", on_pre_tool_call)

    # ── Hook: post_tool_call ────────────────────────────────────────
    def on_post_tool_call(tool_name: str, params: dict, result: str, **kwargs) -> None:
        """Log every tool call for audit trail."""
        # Best-effort logging — failures must not break the agent
        try:
            from maru_deep_pro_search.harness.audit import AuditLogger

            logger = AuditLogger()
            logger.log_tool_call(
                tool_name=tool_name,
                parameters=params,
                result_preview=result[:500] if result else "",
                session_id="hermes",
            )
        except Exception:
            pass

    ctx.register_hook("post_tool_call", on_post_tool_call)

    # ── Hook: on_session_start ──────────────────────────────────────
    def on_session_start(session_id: str, **kwargs) -> None:
        """Reset research gate at the start of a new session."""
        # Remove stale session marker so the user must re-research
        if SESSION_FILE.exists():
            with contextlib.suppress(Exception):
                SESSION_FILE.unlink()
        ctx.inject_message(
            "[MARU-RESEARCH-GATE] New session started. "
            "Run /research <query> before using any tools.",
            role="system",
        )

    ctx.register_hook("on_session_start", on_session_start)

    def _mark_research(query: str) -> None:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "research_id": f"RSCH-{int(datetime.now(timezone.utc).timestamp())}",
            "query": query.strip(),
        }
        SESSION_FILE.write_text(json.dumps(data, indent=2))

    # ── Slash command: /ask ─────────────────────────────────────────
    def cmd_ask(query: str = "") -> str:
        """Trigger answer with the given query."""
        if not query.strip():
            return "Usage: /ask <query>"
        result = ctx.dispatch_tool("answer", {"query": query.strip(), "mode": "balanced"})
        _mark_research(query)
        return f"[MARU] Answer evidence ready. {result}"

    ctx.register_command(
        name="ask",
        handler=cmd_ask,
        description="Answer a general web question with live sources",
    )

    # ── Slash command: /search ──────────────────────────────────────
    def cmd_search(query: str = "") -> str:
        """Trigger web_search with the given query."""
        if not query.strip():
            return "Usage: /search <query>"
        result = ctx.dispatch_tool("web_search", {"query": query.strip()})
        _mark_research(query)
        return f"[MARU] Search completed. {result}"

    ctx.register_command(
        name="search",
        handler=cmd_search,
        description="Run targeted web search",
    )

    # ── Slash command: /compare ─────────────────────────────────────
    def cmd_compare(query: str = "") -> str:
        """Trigger parallel_search with comma-separated query angles."""
        if not query.strip():
            return "Usage: /compare <query A>, <query B>"
        queries = [part.strip() for part in query.split(",") if part.strip()]
        if len(queries) < 2:
            queries = [query.strip(), f"{query.strip()} comparison benchmark"]
        result = ctx.dispatch_tool(
            "parallel_search",
            {"queries": queries[:5], "comparison_mode": True},
        )
        _mark_research(query)
        return f"[MARU] Comparison completed. {result}"

    ctx.register_command(
        name="compare",
        handler=cmd_compare,
        description="Run comparative parallel search",
    )

    # ── Slash command: /research ────────────────────────────────────
    def cmd_research(query: str = "") -> str:
        """Trigger deep_research with the given query."""
        if not query.strip():
            return "Usage: /research <query>"

        result = ctx.dispatch_tool("deep_research", {"query": query.strip()})
        _mark_research(query)

        return f"[MARU] Research completed. {result}"

    ctx.register_command(
        name="research",
        handler=cmd_research,
        description="Run deep research before any code change",
    )

    # ── Slash command: /verify ──────────────────────────────────────
    def cmd_verify() -> str:
        """Check if research has been completed for this session."""
        ok, msg = _check_research()
        if ok:
            return f"[MARU] {msg}"
        return f"[MARU-RESEARCH-GATE] {msg}"

    ctx.register_command(
        name="verify",
        handler=cmd_verify,
        description="Verify research was completed for this session",
    )

    # ── CLI command: hermes maru status ─────────────────────────────
    def cli_status_setup(subparser) -> None:
        subparser.add_argument("--json", action="store_true", help="Output as JSON")

    def cli_status_handler(args) -> int:
        ok, msg = _check_research()
        status = {
            "research_complete": ok,
            "message": msg,
            "session_file": str(SESSION_FILE),
            "ttl_minutes": SESSION_TTL_MINUTES,
        }
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"Maru Research Gate: {'OK' if ok else 'BLOCKED'}")
            print(f"  {msg}")
            print(f"  Session file: {SESSION_FILE}")
            print(f"  TTL: {SESSION_TTL_MINUTES} minutes")
        return 0

    ctx.register_cli_command(
        name="maru",
        help="Maru deep-pro-search research gate commands",
        setup_fn=cli_status_setup,
        handler_fn=cli_status_handler,
    )
