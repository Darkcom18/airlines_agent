"""
MCP Server Entry Point for C1 Travel Agent System.
Exposes travel APIs as MCP tools for LangGraph agents.
Runs as HTTP server for Docker deployment.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import structlog
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
import uvicorn

from config.settings import settings
from .tools import register_all_tools, get_registry

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Global MCP server instance
mcp_server = Server("c1-travel-mcp")

# Register all tools with the registry
registry = register_all_tools()


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return registry.list_tools()


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool call: {name}", arguments=arguments)

    try:
        result = await registry.call(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# SSE transport
sse_transport = SseServerTransport("/messages")


async def handle_sse(request):
    """Handle SSE connections for MCP."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options()
        )


async def handle_messages(request):
    """Handle POST messages for MCP."""
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


async def health(_request):
    """Health check endpoint."""
    stats = registry.get_domain_stats()
    total_tools = sum(stats.values())
    return JSONResponse({
        "status": "healthy",
        "service": "c1-travel-mcp",
        "total_tools": total_tools,
        "domains": stats,
        "tools": registry.list_tool_names()
    })


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/sse", handle_sse, methods=["GET"]),
        Route("/messages", handle_messages, methods=["POST"]),
    ]
)


def main():
    """Run the MCP server."""
    stats = registry.get_domain_stats()
    total_tools = sum(stats.values())
    logger.info(f"Starting C1 Travel MCP Server on port 8001...")
    logger.info(f"Total tools registered: {total_tools}")
    logger.info(f"Domain stats: {stats}")
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
