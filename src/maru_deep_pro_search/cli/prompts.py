"""Research protocol prompt templates injected into each agent."""

from __future__ import annotations

import datetime
import re

_CURRENT_YEAR = datetime.datetime.now(tz=datetime.timezone.utc).year

# Unique markers that wrap the protocol so adapters can surgically replace it
# even when the language or content changes between versions.
PROTOCOL_START_MARKER = "<!-- MARU-RESEARCH-PROTOCOL-START -->"
PROTOCOL_END_MARKER = "<!-- MARU-RESEARCH-PROTOCOL-END -->"

# The unified research-first protocol injected as system prompt / rules.
# English only — token-efficient and optimal for all LLMs.
_RESEARCH_PROTOCOL_BODY = f"""MANDATORY RESEARCH PROTOCOL — DO NOT VIOLATE

Rule 1: Before answering ANY technical question, you MUST call
        maru-deep-pro-search's deep_research(query) tool.

Rule 2: NEVER include past years (2024, 2023, etc.) in the query passed
        to deep_research. Use the current year ({_CURRENT_YEAR}), "latest",
        "current", or "recent" only. maru-deep-pro-search automatically
        finds the most up-to-date results.

Rule 3: After receiving research results, analyze ALL sources and cite
        them in your answer using [1], [2], [3] format.

Rule 4: If results are insufficient or contradictory, call deep_research
        again with a refined query. NEVER guess.

Rule 5: For comparison questions ("A vs B"), use parallel_search for
        multi-angle research: ["A advantages", "B advantages",
        "A vs B benchmark {_CURRENT_YEAR}"].

Rule 6: For code / library questions, verify the latest version and API
        via deep_research BEFORE writing any code.

Rule 7: Your training data is stale. The web is current.
        Always verify freshness with deep_research."""

RESEARCH_PROTOCOL = f"{PROTOCOL_START_MARKER}\n{_RESEARCH_PROTOCOL_BODY}\n{PROTOCOL_END_MARKER}"

# Regex that matches ANY previously injected protocol block (Korean or English,
# old or new) so adapters can remove it before inserting the latest version.
_PROTOCOL_BLOCK_RE = re.compile(
    re.escape(PROTOCOL_START_MARKER) + r".*?" + re.escape(PROTOCOL_END_MARKER),
    re.DOTALL,
)


# Agent-specific wrappers (if an agent needs the protocol formatted differently)
CLAUDE_SYSTEM_PROMPT_APPENDIX = f"""

{RESEARCH_PROTOCOL}
"""

CURSOR_RULES_APPENDIX = f"""

# maru-deep-pro-search Research Protocol
{RESEARCH_PROTOCOL}
"""

KIMI_SKILL_PROMPT = RESEARCH_PROTOCOL

WINDSURF_RULES_APPENDIX = CURSOR_RULES_APPENDIX


AIDER_CONVENTIONS_APPENDIX = f"""
# Aider Coding Conventions — Research-First Development

{RESEARCH_PROTOCOL}

## Additional Aider-Specific Rules
- Before any /code or /add command, ensure deep_research has been run.
- Use /test to verify implementation against research findings.
- Do not use /commit until all citations [1], [2] are verified.
"""

COPILOT_INSTRUCTIONS_APPENDIX = f"""
# GitHub Copilot Instructions — Research-First Coding

{RESEARCH_PROTOCOL}

## Copilot-Specific Guidance
- When suggesting completions, prioritize patterns found in deep_research results.
- Inline comments should reference research citations when explaining technical decisions.
- Do not suggest deprecated APIs or patterns contradicted by research.
"""


def strip_existing_protocol(text: str) -> str:
    """Remove any previously injected research protocol block from *text*.

    This handles both the new marker-wrapped protocol and legacy Korean
    protocol that was injected before the marker system existed.  It is
    deliberately forgiving so that minor formatting changes between
    versions do not cause duplicate injection.
    """
    # 1. Remove any block wrapped in our official markers (works for any language).
    cleaned = _PROTOCOL_BLOCK_RE.sub("", text)

    # 2. Heuristic: remove the old Korean protocol header + body.
    #    The old protocol started with "═══..." and contained "필수 리서치 프로토콜".
    #    We strip from the first "═" border line to the last one.
    if "필수 리서치 프로토콜" in cleaned or "MANDATORY RESEARCH PROTOCOL" in cleaned:
        # Remove content between ═══ border lines that contain protocol keywords
        cleaned = re.sub(
            r"═+\n?[^═]*(?:필수 리서치 프로토콜|MANDATORY RESEARCH PROTOCOL)[^═]*═+.*?═+",
            "",
            cleaned,
            flags=re.DOTALL,
        )
        # Also clean up stray border-only blocks left behind
        cleaned = re.sub(r"═+\s*", "", cleaned)

    # Normalise excessive blank lines left behind by the removal
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def inject_protocol(content: str, protocol: str) -> str:
    """Return *content* with *protocol* injected, replacing any old version.

    This is the canonical helper that every adapter should use in
    ``inject_rules()`` instead of manual ``if protocol not in content`` checks.
    """
    cleaned = strip_existing_protocol(content)
    return f"{cleaned}\n\n{protocol}\n" if cleaned else f"{protocol}\n"


def get_protocol_for_agent(agent: str) -> str:
    """Return the research protocol formatted for the given agent."""
    mapping = {
        "claude": CLAUDE_SYSTEM_PROMPT_APPENDIX,
        "cursor": CURSOR_RULES_APPENDIX,
        "windsurf": WINDSURF_RULES_APPENDIX,
        "kimi": KIMI_SKILL_PROMPT,
        "aider": AIDER_CONVENTIONS_APPENDIX,
        "copilot": COPILOT_INSTRUCTIONS_APPENDIX,
        "antigravity": RESEARCH_PROTOCOL,
        "kilo": RESEARCH_PROTOCOL,
        "opencode": RESEARCH_PROTOCOL,
        "continue": RESEARCH_PROTOCOL,
        "cline": RESEARCH_PROTOCOL,
        "zed": RESEARCH_PROTOCOL,
        "jetbrains": RESEARCH_PROTOCOL,
        "supermaven": RESEARCH_PROTOCOL,
        "cody": RESEARCH_PROTOCOL,
        "codeium": RESEARCH_PROTOCOL,
        "amazon_q": RESEARCH_PROTOCOL,
        "devin": RESEARCH_PROTOCOL,
        "tabnine": RESEARCH_PROTOCOL,
        "codex": RESEARCH_PROTOCOL,
    }
    return mapping.get(agent, RESEARCH_PROTOCOL)
