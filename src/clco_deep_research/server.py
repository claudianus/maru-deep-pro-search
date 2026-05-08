"""MCP server entry point for clco-deep-research.

Scrapling-native search: directly crawls search engine SERPs, fetches pages,
and extracts LLM-optimized content. No API wrappers, no API key requirements.

Run:
    uvx clco-deep-research-mcp
    python -m clco_deep_research.server
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server

from .tools import TOOLS

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

server = Server("clco-deep-research")


@server.list_tools()
async def handle_list_tools() -> list[dict[str, Any]]:
    """List all available tools with their schemas."""
    return [
        {"name": name, "description": desc, "inputSchema": schema}
        for name, (_handler, desc, schema) in TOOLS.items()
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
    """Execute a tool by name with the given arguments."""
    if name not in TOOLS:
        return [{
            "type": "text",
            "text": f"Error: Unknown tool '{name}'. Available tools: {', '.join(TOOLS.keys())}"
        }]

    handler, _desc, _schema = TOOLS[name]

    try:
        result = await handler(**arguments)
        return [{"type": "text", "text": result}]
    except Exception as e:
        logging.exception("Tool '%s' failed: %s", name, e)
        return [{"type": "text", "text": f"Error executing '{name}': {e}"}]


async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="clco-deep-research",
                server_version="0.3.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
