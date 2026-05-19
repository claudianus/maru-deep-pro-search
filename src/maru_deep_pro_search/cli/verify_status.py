"""Read-only verification for ``setup --check`` (never writes config)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.base import AgentAdapter
from .agents.codex import CodexAdapter
from .backup import read_json_safe, read_text_safe
from .prompts import PROTOCOL_START_MARKER, text_has_research_protocol


def rules_text_ok(text: str) -> bool:
    return text_has_research_protocol(text)


def yaml_mcp_ok(data: dict[str, Any]) -> bool:
    mcp = data.get("mcpServers")
    return isinstance(mcp, dict) and "maru-deep-pro-search" in mcp


def json_mcp_ok(config: dict[str, Any]) -> bool:
    mcp_servers = config.get("mcpServers")
    if isinstance(mcp_servers, dict) and "maru-deep-pro-search" in mcp_servers:
        return True
    mcp = config.get("mcp")
    if isinstance(mcp, dict) and "maru-deep-pro-search" in mcp:
        return True
    ctx = config.get("context_servers")
    if isinstance(ctx, dict) and "maru-deep-pro-search" in ctx:
        return True
    server = config.get("server")
    if isinstance(server, dict):
        mcp_servers = server.get("mcpServers")
        if isinstance(mcp_servers, dict) and "maru-deep-pro-search" in mcp_servers:
            return True
    experimental = config.get("experimental")
    if isinstance(experimental, dict):
        lst = experimental.get("modelContextProtocolServers")
        if isinstance(lst, list) and any(
            isinstance(e, dict) and e.get("name") == "maru-deep-pro-search" for e in lst
        ):
            return True
    return False


def _rules_path_ok(path: Path) -> bool:
    return path.exists() and rules_text_ok(read_text_safe(path))


def verify_adapter(adapter: AgentAdapter, scope: str = "user") -> dict[str, bool]:
    """Dispatch read-only checks by adapter name."""
    name = adapter.name

    if name == "continue":
        from .agents.continue_ import ContinueAdapter

        if isinstance(adapter, ContinueAdapter):
            return adapter.verify_setup(scope)

    if name in ("copilot", "amazon_q", "cody", "codeium", "devin", "supermaven", "tabnine"):
        return _verify_rules_only(adapter, scope)

    if name == "jetbrains":
        rule = Path.home() / ".aiassistant" / "rules" / "maru-research-protocol.md"
        return {"mcp": True, "rules": _rules_path_ok(rule)}

    if name == "hermes":
        hermes_config = Path.home() / ".hermes" / "config.yaml"
        soul = Path.home() / ".hermes" / "SOUL.md"
        content = read_text_safe(hermes_config)
        return {
            "mcp": "maru-deep-pro-search:" in content,
            "rules": rules_text_ok(read_text_safe(soul))
            or "MARU-RESEARCH-PROTOCOL-START" in content,
        }

    if name == "codex":
        codex_config = Path.home() / ".codex" / "config.toml"
        agents = Path.home() / ".codex" / "AGENTS.md"
        text = read_text_safe(codex_config)
        lines = text.splitlines() if text else []
        first_table = CodexAdapter._first_table_header_index(lines)
        root_text = "\n".join(lines[:first_table])
        config_rules_ok = CodexAdapter.developer_instructions_at_root(lines) and (
            PROTOCOL_START_MARKER in root_text
        )
        return {
            "mcp": "[mcp_servers.maru-deep-pro-search]" in text,
            "rules": rules_text_ok(read_text_safe(agents)) or config_rules_ok,
        }

    if name == "kimi":
        mcp = Path.home() / ".kimi" / "mcp.json"
        toml = Path.home() / ".kimi" / "config.toml"
        return {
            "mcp": json_mcp_ok(read_json_safe(mcp)),
            "rules": "# MARU-SYSTEM-PROMPT" in read_text_safe(toml),
        }

    if name == "cline":
        mcp = Path.home() / ".cline" / "mcp.json"
        hook = Path.home() / ".cline" / "hooks" / "PreToolUse"
        rules = Path.home() / "Documents" / "Cline" / "Rules" / "maru-research-protocol.md"
        if not rules.exists():
            rules = Path(".clinerules") / "maru-research-protocol.md"
        return {
            "mcp": json_mcp_ok(read_json_safe(mcp)),
            "rules": _rules_path_ok(rules) and hook.exists(),
        }

    if name == "aider":
        conv = Path.home() / ".aider" / "CONVENTIONS.md"
        conf = Path.home() / ".aider.conf.yml"
        return {
            "mcp": True,
            "rules": rules_text_ok(read_text_safe(conv))
            or "maru_research_gate" in read_text_safe(conf),
        }

    if name == "antigravity":
        mcp = Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
        sidecar = mcp.parent / "MARU_RESEARCH_PROTOCOL.md"
        return {
            "mcp": json_mcp_ok(read_json_safe(mcp)),
            "rules": _rules_path_ok(sidecar),
        }

    if name == "zed":
        settings = Path.home() / ".config" / "zed" / "settings.json"
        assistant = Path.home() / ".config" / "zed" / "assistant.md"
        return {
            "mcp": json_mcp_ok(read_json_safe(settings)),
            "rules": rules_text_ok(read_text_safe(assistant)),
        }

    json_mcp_paths: dict[str, tuple[Path, Path | None]] = {
        "claude": (Path.home() / ".claude" / ".mcp.json", Path.home() / ".claude" / "CLAUDE.md"),
        "cursor": (
            Path.home() / ".cursor" / "mcp.json",
            Path.home() / ".cursor" / "rules" / "maru-research-protocol.md",
        ),
        "windsurf": (
            Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
            Path.home() / ".windsurf" / "rules" / "maru-research-protocol.md",
        ),
        "opencode": (
            Path.home() / ".config" / "opencode" / "opencode.json",
            Path.home() / ".config" / "opencode" / "AGENTS.md",
        ),
        "kilo": (
            Path.home() / ".config" / "kilo" / "kilo.jsonc",
            None,
        ),
    }
    if name in json_mcp_paths:
        mcp_path, rules_path = json_mcp_paths[name]
        rules_ok = _rules_path_ok(rules_path) if rules_path else False
        if name == "kilo":
            kilo_config = read_json_safe(mcp_path)
            rules_ok = rules_text_ok(str(kilo_config.get("systemPrompt", "")))
        return {"mcp": json_mcp_ok(read_json_safe(mcp_path)), "rules": rules_ok}

    return {"mcp": True, "rules": True}


def _verify_rules_only(adapter: AgentAdapter, scope: str) -> dict[str, bool]:
    paths_by_name: dict[str, list[Path]] = {
        "copilot": [
            Path.home() / ".copilot" / "instructions" / "maru-research-protocol.instructions.md"
        ],
        "amazon_q": [Path.home() / ".amazonq" / "rules" / "maru-research-protocol.md"],
        "cody": [Path.home() / ".cody" / "cody_instructions.md"],
        "codeium": [Path.home() / ".codeium" / "instructions.md"],
        "devin": [Path.home() / ".devin" / "instructions.md"],
        "supermaven": [Path.home() / ".supermaven" / "instructions.md"],
        "tabnine": [Path.home() / ".tabnine" / "guidelines" / "maru-research-protocol.md"],
    }
    ok = any(_rules_path_ok(p) for p in paths_by_name.get(adapter.name, []))
    return {"mcp": True, "rules": ok}
