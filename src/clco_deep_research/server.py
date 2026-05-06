"""MCP server entry point for clco-deep-research.

Scrapling-native search: directly crawls search engine SERPs, fetches pages,
and extracts LLM-optimized content. No API wrappers, no API key requirements
(except Brave if configured).

Run:
    uvx clco-deep-research-mcp
    python -m clco_deep_research.server
"""

from typing import Any

from mcp.server import Server
from mcp.server.models import ServerCapabilities
from mcp.server.stdio import stdio_server

from .tools import TOOLS

server = Server("clco-deep-research")


@server.list_tools()
async def handle_list_tools() -> list[dict[str, Any]]:
    return [
        {"name": name, "description": desc, "inputSchema": schema}
        for name, (_handler, desc, schema) in TOOLS.items()
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")

    handler, _desc, _schema = TOOLS[name]
    try:
        result = await handler(**arguments)
    except Exception as e:
        return [{"type": "text", "text": f"Error: {e}"}]

    return [{"type": "text", "text": result}]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            ServerCapabilities(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
