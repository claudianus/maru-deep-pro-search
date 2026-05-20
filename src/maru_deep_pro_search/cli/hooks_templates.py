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
    if any(line.startswith(MARU_MANAGED_PREFIX) for line in body.splitlines()[:2]):
        stamped = body
    elif body.startswith("#!"):
        parts = body.split("\n", 1)
        shebang = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        stamped = f"{shebang}\n{managed_version_line()}{rest}"
    else:
        stamped = f"{managed_version_line()}{body}"

    if path.exists() and not force and not is_managed_hook(path):
        return False
    if path.exists() and not force and not hook_script_stale(path):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stamped, encoding="utf-8")
    path.chmod(0o755)
    return True


def _freshness_gate_script(title: str) -> str:
    return f'''#!/usr/bin/env python3
"""{title}"""
from __future__ import annotations

import json
import os
import shlex
import sys
import time
from collections.abc import Mapping
from typing import Any

MARKER = os.path.expanduser("~/.maru/last_research")
TTL_SECONDS = 1800

RESEARCH_TOOL_NAMES = {{
    "BrowserAction",
    "WebFetch",
    "WebSearch",
    "brave_search",
    "browser_action",
    "browser_search",
    "chrome-devtools-mcp",
    "fetch_page",
    "google_search",
    "search_web",
}}
MARU_RESEARCH_TOOL_NAMES = {{"answer", "deep_research", "parallel_search", "web_search"}}
LOCAL_MCP_TOOLS = {{
    "ctx_graph",
    "ctx_knowledge",
    "ctx_overview",
    "ctx_read",
    "ctx_search",
    "ctx_session",
    "ctx_tree",
}}
LOCAL_SHELL_COMMANDS = {{
    "awk",
    "date",
    "file",
    "gh",
    "git",
    "jq",
    "lean-ctx",
    "ls",
    "mypy",
    "pwd",
    "python",
    "python3",
    "rg",
    "ruff",
    "sed",
    "uv",
}}
NETWORK_SHELL_COMMANDS = {{"curl", "http", "httpie", "links", "lynx", "w3m", "wget"}}
PACKAGE_FRESHNESS_COMMANDS = {{
    ("npm", "info"),
    ("npm", "view"),
    ("pip", "index"),
    ("pip3", "index"),
    ("pnpm", "info"),
    ("pnpm", "view"),
    ("yarn", "info"),
}}


def _load_event() -> dict[str, Any] | None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _get_string(data: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    for container_key in ("tool_input", "agent_action_input", "input", "arguments", "params", "tool", "mcp"):
        value = data.get(container_key)
        if isinstance(value, Mapping):
            nested = _get_string(value, *keys)
            if nested:
                return nested
    return ""


def _shell_words(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _unwrap_shell_command(command: str) -> str:
    words = _shell_words(command)
    if len(words) >= 3 and words[0] == "lean-ctx" and words[1] == "-c":
        return words[2]
    return command


def _shell_requires_research(command: str) -> bool:
    command = _unwrap_shell_command(command).strip()
    if not command:
        return False
    words = _shell_words(command)
    if not words:
        return False
    executable = os.path.basename(words[0])
    second = words[1] if len(words) > 1 else ""
    if (executable, second) in PACKAGE_FRESHNESS_COMMANDS:
        return True
    if executable == "gh" and second == "search":
        return True
    if executable in NETWORK_SHELL_COMMANDS:
        return True
    return False


def _mcp_requires_research(data: Mapping[str, Any]) -> bool:
    tool_name = _get_string(data, "toolName", "tool_name", "tool", "name")
    server_name = _get_string(data, "server", "serverName", "server_name", "mcpServer")
    normalized_tool = tool_name.lower()
    normalized_server = server_name.lower()
    if tool_name in MARU_RESEARCH_TOOL_NAMES or tool_name in LOCAL_MCP_TOOLS:
        return False
    if tool_name in RESEARCH_TOOL_NAMES:
        return True
    if "lean-ctx" in normalized_server:
        return normalized_tool not in LOCAL_MCP_TOOLS
    if "context7" in normalized_server:
        return True
    if "browser" in normalized_server and "search" in normalized_tool:
        return True
    if "deep-pro-search" in normalized_server or "maru-deep-pro-search" in normalized_server:
        return normalized_tool not in MARU_RESEARCH_TOOL_NAMES
    return False


def _requires_research(data: Mapping[str, Any] | None) -> tuple[bool, str]:
    if data is None:
        return True, "unparseable hook payload"
    command = _get_string(data, "command")
    if command:
        return _shell_requires_research(command), "shell command '" + _unwrap_shell_command(command) + "'"
    return _mcp_requires_research(data), "tool '" + (
        _get_string(data, "toolName", "tool_name", "tool", "name") or "unknown"
    ) + "'"


def _research_age() -> float | None:
    if not os.path.exists(MARKER):
        return None
    return time.time() - os.path.getmtime(MARKER)


def main() -> None:
    requires_research, reason = _requires_research(_load_event())
    if not requires_research:
        sys.exit(0)
    elapsed = _research_age()
    if elapsed is None or elapsed > TTL_SECONDS:
        prefix = "[MARU] Research required" if elapsed is None else "[MARU] Research expired"
        print(
            prefix + " for " + reason + ". Run answer or deep_research first. "
            "Local reads, edits, and validation are allowed.",
            file=sys.stderr,
        )
        sys.exit(2)
    print("[MARU] WARNING: Fresh research exists; allowing " + reason + ".", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
'''


def claude_research_gate() -> str:
    return _freshness_gate_script(
        "Claude Code PreToolUse hook — gates only freshness-sensitive search/network actions."
    )


def claude_research_revert() -> str:
    return '''#!/usr/bin/env python3
"""Claude Code PostToolUse hook — compatibility no-op for old research gates."""
import sys

def main() -> None:
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
    return _freshness_gate_script(
        "Windsurf Cascade hook — gates only freshness-sensitive search/network actions."
    )


def kimi_research_gate() -> str:
    return _freshness_gate_script(
        "Kimi PreToolUse hook — gates only freshness-sensitive search/network actions."
    )


def aider_research_gate() -> str:
    return '''#!/usr/bin/env python3
"""Aider compatibility hook — no longer blocks local edits or validation."""
import sys


def main() -> int:
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def antigravity_research_gate() -> str:
    return _freshness_gate_script(
        "Antigravity PreToolUse hook — gates only freshness-sensitive search/network actions."
    )


def cursor_research_gate() -> str:
    return _freshness_gate_script(
        "Cursor pre-execution hook — gates only freshness-sensitive search/network actions."
    )


_HOOK_BODIES: dict[str, Callable[[], str]] = {
    "claude_research_gate": claude_research_gate,
    "claude_research_revert": claude_research_revert,
    "claude_session_start": claude_session_start,
    "windsurf_research_gate": windsurf_research_gate,
    "kimi_research_gate": kimi_research_gate,
    "aider_research_gate": aider_research_gate,
    "antigravity_research_gate": antigravity_research_gate,
    "cursor_research_gate": cursor_research_gate,
}


def template_body(name: str) -> str:
    factory = _HOOK_BODIES.get(name)
    if factory is None:
        msg = f"unknown hook template: {name}"
        raise KeyError(msg)
    return factory()
