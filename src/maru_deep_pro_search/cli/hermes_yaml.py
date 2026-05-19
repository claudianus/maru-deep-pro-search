"""Structured YAML merge helpers for Hermes ``config.yaml``."""

from __future__ import annotations

import re
from typing import Any

import yaml

from .agents.base import get_mcp_server_command

MARU_MCP_MARKER = "# maru-deep-pro-search MCP"
MARU_SHELL_HOOKS_MARKER = "# maru-shell-hooks"
MARU_AUDIT_ARGS = ["[MARU-AUDIT] tool executed"]

_PROTOCOL_RE = re.compile(
    r"# MARU-RESEARCH-PROTOCOL-START.*?# MARU-RESEARCH-PROTOCOL-END\n",
    re.DOTALL,
)
_MARU_SHELL_HOOKS_RE = re.compile(
    rf"\n{re.escape(MARU_SHELL_HOOKS_MARKER)}\nhooks:\n(?:[ \t].*\n)*",
)


def split_protocol_preamble(content: str) -> tuple[str, str]:
    """Split MARU protocol comment block from the rest of the YAML body."""
    match = _PROTOCOL_RE.search(content)
    if not match:
        return "", content
    return match.group(0), content[match.end() :]


def strip_maru_eof_blocks(body: str) -> str:
    """Remove legacy EOF ``hooks:`` append blocks managed by maru setup."""
    return _MARU_SHELL_HOOKS_RE.sub("\n", body).rstrip()


def has_legacy_eof_shell_hooks(content: str) -> bool:
    """True when the old EOF ``# maru-shell-hooks`` append block is still present."""
    return MARU_SHELL_HOOKS_MARKER in content


def load_hermes_config(content: str) -> tuple[str, dict[str, Any]]:
    """Parse Hermes config into preamble text and a mutable mapping."""
    preamble, body = split_protocol_preamble(content)
    body = strip_maru_eof_blocks(body)
    raw = yaml.safe_load(body) if body.strip() else {}
    if not isinstance(raw, dict):
        raw = {}
    return preamble, raw


def dump_hermes_config(preamble: str, data: dict[str, Any]) -> str:
    """Serialize Hermes config with optional protocol preamble."""
    dumped = str(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    )
    if preamble:
        return f"{preamble}\n{dumped}"
    return dumped


def mcp_server_entry() -> dict[str, Any]:
    spec = get_mcp_server_command()
    return {
        "command": spec["command"],
        "args": list(spec.get("args") or []),
    }


def merge_mcp_servers(data: dict[str, Any]) -> None:
    servers = data.setdefault("mcp_servers", {})
    if not isinstance(servers, dict):
        servers = {}
        data["mcp_servers"] = servers
    if "maru-deep-pro-search" not in servers:
        servers["maru-deep-pro-search"] = mcp_server_entry()


def merge_plugins(data: dict[str, Any]) -> None:
    plugins = data.setdefault("plugins", {})
    if not isinstance(plugins, dict):
        plugins = {}
        data["plugins"] = plugins
    enabled = plugins.setdefault("enabled", [])
    if not isinstance(enabled, list):
        enabled = []
        plugins["enabled"] = enabled
    if "maru-research-gate" not in enabled:
        enabled.append("maru-research-gate")


def merge_shell_hooks(data: dict[str, Any]) -> None:
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks
    post_tool_call = hooks.setdefault("post_tool_call", [])
    if not isinstance(post_tool_call, list):
        post_tool_call = []
        hooks["post_tool_call"] = post_tool_call
    audit = {"command": "echo", "args": list(MARU_AUDIT_ARGS)}
    if not any(
        isinstance(item, dict)
        and item.get("command") == audit["command"]
        and item.get("args") == audit["args"]
        for item in post_tool_call
    ):
        post_tool_call.append(audit)


def upsert_protocol_preamble(content: str, protocol_yaml: str) -> str:
    """Insert or replace the MARU protocol comment preamble."""
    if "MARU-RESEARCH-PROTOCOL-START" in content:
        return _PROTOCOL_RE.sub(protocol_yaml, content, count=1)
    return f"{protocol_yaml}\n{content}" if content else protocol_yaml
