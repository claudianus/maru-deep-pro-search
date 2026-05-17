"""Versioned hook script templates for maru-managed agent gate files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from maru_deep_pro_search import __version__

MARU_MANAGED_PREFIX = "# maru-managed:"


def managed_version_line() -> str:
    return f"{MARU_MANAGED_PREFIX} {__version__}\n"


def is_managed_hook(path: Path) -> bool:
    """True if the file carries a maru-managed version stamp."""
    if not path.is_file():
        return False
    try:
        head = path.read_text(encoding="utf-8")[:512]
    except OSError:
        return False
    return MARU_MANAGED_PREFIX in head


def read_managed_version(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[:8]:
            if line.startswith(MARU_MANAGED_PREFIX):
                return line[len(MARU_MANAGED_PREFIX) :].strip()
    except OSError:
        return None
    return None


def hook_script_stale(path: Path, expected_version: str | None = None) -> bool:
    """True when a managed hook is missing, unstamped, or on an older package version."""
    expected = expected_version or __version__
    if not path.is_file():
        return True
    if not is_managed_hook(path):
        return True
    found = read_managed_version(path)
    return found is None or found != expected


def write_managed_hook(path: Path, body: str, *, force: bool = False) -> bool:
    """Write *body* with a version stamp. Skips non-managed existing files unless *force*."""
    stamped = (
        body if MARU_MANAGED_PREFIX in body.split("\n", 2)[0] else f"{managed_version_line()}{body}"
    )
    if path.exists() and not force and not is_managed_hook(path):
        return False
    if path.exists() and not force and not hook_script_stale(path):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stamped, encoding="utf-8")
    path.chmod(0o755)
    return True


def claude_research_gate() -> str:
    return '''#!/usr/bin/env python3
"""Claude Code PreToolUse hook — blocks Bash without research."""
import json, os, sys, time

def main() -> None:
    data = json.load(sys.stdin)
    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)
    marker = os.path.expanduser("~/.maru/last_research")
    if not os.path.exists(marker):
        print("[MARU] Research required. Call answer or deep_research before running commands.", file=sys.stderr)
        sys.exit(2)
    elapsed = time.time() - os.path.getmtime(marker)
    if elapsed > 1800:
        print(f"[MARU] Research expired ({elapsed/60:.0f}min ago). Re-run answer or deep_research.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
'''


def claude_research_revert() -> str:
    return '''#!/usr/bin/env python3
"""Claude Code PostToolUse hook — reverts Write/Edit without research."""
import json, os, subprocess, sys

def main() -> None:
    data = json.load(sys.stdin)
    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)
    marker = os.path.expanduser("~/.maru/last_research")
    ok = False
    if os.path.exists(marker):
        import time
        if time.time() - os.path.getmtime(marker) <= 1800:
            ok = True
    if ok:
        sys.exit(0)
    file_path = data.get("tool_input", {}).get("file_path", "")
    if file_path:
        subprocess.run(["git", "checkout", "--", file_path], capture_output=True)
    print("[MARU-POST-GATE] Reverted un-researched edit. Run /research first.", file=sys.stderr)
    sys.exit(0)

if __name__ == "__main__":
    main()
'''


def claude_session_start() -> str:
    return '''#!/usr/bin/env python3
"""Claude Code SessionStart hook — inject research reminder."""
import json, sys

def main() -> None:
    print(json.dumps({
        "additionalContext": "[MARU-RESEARCH-GATE] New session. Run answer or deep_research before code changes."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
'''


def windsurf_research_gate() -> str:
    return '''#!/usr/bin/env python3
"""Windsurf Cascade Hook — blocks edits/tool-calls without research."""
import json
import os
import sys
import time

MARKER = os.path.expanduser("~/.maru/last_research")
TTL_SECONDS = 1800

def main() -> None:
    data = json.load(sys.stdin)
    action = data.get("agent_action_name", "")
    if action not in ("pre_write_code", "pre_mcp_tool_use", "pre_user_prompt"):
        sys.exit(0)
    if not os.path.exists(MARKER):
        print("[MARU] Research required. Call answer or deep_research first.", file=sys.stderr)
        sys.exit(2)
    elapsed = time.time() - os.path.getmtime(MARKER)
    if elapsed > TTL_SECONDS:
        print(f"[MARU] Research expired ({elapsed/60:.0f}min). Re-run answer or deep_research.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
'''


def kimi_research_gate() -> str:
    return '''#!/usr/bin/env python3
"""Kimi PreToolUse hook — blocks edits without research."""
import json
import os
import sys
import time

MARKER = os.path.expanduser("~/.maru/last_research")
TTL_SECONDS = 1800

def main() -> None:
    data = json.load(sys.stdin)
    event = data.get("event", "")
    if event != "PreToolUse":
        sys.exit(0)
    tool = data.get("tool", "")
    if tool not in ("WriteFile", "ApplyDiff", "Shell", "BrowserAction"):
        sys.exit(0)
    if not os.path.exists(MARKER):
        print("[MARU] Research required. Call answer or deep_research first.", file=sys.stderr)
        sys.exit(1)
    elapsed = time.time() - os.path.getmtime(MARKER)
    if elapsed > TTL_SECONDS:
        print(f"[MARU] Research expired ({elapsed/60:.0f}min). Re-run answer or deep_research.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
'''


def aider_research_gate() -> str:
    return '''#!/usr/bin/env python3
"""Aider lint-cmd research gate — blocks edits when research incomplete."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SESSION_FILE = Path.home() / ".maru" / "session_research.json"
SESSION_TTL_MINUTES = int(os.environ.get("MARU_RESEARCH_TTL", "30"))


def _fail(msg: str) -> None:
    print(f"[MARU-RESEARCH-GATE] ERROR: {msg}", file=sys.stderr)
    print(
        "[MARU-RESEARCH-GATE] Run answer or deep_research first.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> int:
    if not SESSION_FILE.exists():
        _fail("No research session found. Research must be completed before editing.")
    try:
        data = json.loads(SESSION_FILE.read_text())
    except Exception:
        _fail("Corrupted session research file.")
    completed_at = data.get("completed_at")
    if not completed_at:
        _fail("Research not marked as completed.")
    try:
        ts = datetime.fromisoformat(completed_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        _fail(f"Invalid timestamp: {completed_at}")
    now = datetime.now(timezone.utc)
    if now - ts > timedelta(minutes=SESSION_TTL_MINUTES):
        _fail(
            f"Research expired (TTL={SESSION_TTL_MINUTES}min). "
            "Re-run answer or deep_research before editing."
        )
    rid = data.get("research_id", "")
    if not rid.startswith("RSCH-"):
        _fail(f"Invalid research_id format: {rid}")
    print(f"[MARU-RESEARCH-GATE] OK — research {rid} valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


_HOOK_BODIES: dict[str, Callable[[], str]] = {
    "claude_research_gate": claude_research_gate,
    "claude_research_revert": claude_research_revert,
    "claude_session_start": claude_session_start,
    "windsurf_research_gate": windsurf_research_gate,
    "kimi_research_gate": kimi_research_gate,
    "aider_research_gate": aider_research_gate,
}


def template_body(name: str) -> str:
    factory = _HOOK_BODIES.get(name)
    if factory is None:
        msg = f"unknown hook template: {name}"
        raise KeyError(msg)
    return factory()
