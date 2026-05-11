"""Research protocol prompt templates injected into each agent."""

from __future__ import annotations

import datetime

_CURRENT_YEAR = datetime.datetime.now(tz=datetime.timezone.utc).year

# The unified research-first protocol injected as system prompt / rules.
# English only — token-efficient and optimal for all LLMs.
RESEARCH_PROTOCOL = f"""═══════════════════════════════════════════════════════════════
MANDATORY RESEARCH PROTOCOL — DO NOT VIOLATE
═══════════════════════════════════════════════════════════════

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
        Always verify freshness with deep_research.

═══════════════════════════════════════════════════════════════"""


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
    }
    return mapping.get(agent, RESEARCH_PROTOCOL)
