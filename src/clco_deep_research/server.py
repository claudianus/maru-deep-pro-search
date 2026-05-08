from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("clco-deep-research")

_logger = logging.getLogger("clco_deep_research")
_logger.setLevel(logging.INFO)

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
_logger.addHandler(_stderr_handler)
_logger.propagate = False


@mcp.tool()
async def web_search(
    query: str,
    engine: str = "duckduckgo_lite",
    max_results: int = 10,
) -> str:
    from .tools import tool_web_search

    return await tool_web_search(query, engine, max_results)


@mcp.tool()
async def fetch_page(url: str, stealth: bool = False, max_tokens: int = 3000) -> str:
    from .tools import tool_fetch_page

    return await tool_fetch_page(url, stealth, max_tokens)


@mcp.tool()
async def fetch_bulk(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = 5,
    max_tokens: int = 1500,
) -> str:
    from .tools import tool_fetch_bulk

    return await tool_fetch_bulk(urls, stealth, max_concurrent, max_tokens)


@mcp.tool()
async def deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 8,
    follow_links: bool = False,
    expand_queries: bool = True,
) -> str:
    from .tools import tool_deep_research

    return await tool_deep_research(
        query, engine, max_sources, follow_links, expand_queries
    )


@mcp.tool()
async def stealthy_fetch(url: str, max_tokens: int = 3000) -> str:
    from .tools import tool_stealthy_fetch

    return await tool_stealthy_fetch(url, max_tokens)


@mcp.tool()
async def parallel_search(
    queries: list[str],
    engine: str = "duckduckgo_lite",
    max_results: int = 5,
) -> str:
    from .tools import tool_parallel_search

    return await tool_parallel_search(queries, engine, max_results)


def run() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
