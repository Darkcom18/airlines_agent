"""
Tool Registry for C1 Travel Agent System.
Centralized registry for all 52 MCP tools organized by domain.
"""
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from mcp.types import Tool
import structlog

logger = structlog.get_logger()


class ToolDomain(str, Enum):
    """Tool domains/categories."""
    FLIGHT_SEARCH = "flight_search"
    FLIGHT_INFO = "flight_info"
    BOOKING = "booking"
    TICKETING = "ticketing"
    PNR_MANAGEMENT = "pnr_management"
    ANCILLARY = "ancillary"
    POST_SALES = "post_sales"
    UTILITY = "utility"


@dataclass
class ToolDefinition:
    """Complete tool definition with metadata."""
    tool: Tool
    domain: ToolDomain
    handler: Callable
    description: str
    requires_auth: bool = False
    rate_limit: int = 100  # requests per minute
    cache_ttl: int = 0  # seconds, 0 = no cache
    tags: list = field(default_factory=list)


class ToolRegistry:
    """
    Central registry for all MCP tools.
    Provides tool lookup, domain filtering, and handler dispatch.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._domain_index: Dict[ToolDomain, list] = {d: [] for d in ToolDomain}

    def register(
        self,
        name: str,
        tool: Tool,
        handler: Callable,
        domain: ToolDomain,
        description: str = "",
        requires_auth: bool = False,
        rate_limit: int = 100,
        cache_ttl: int = 0,
        tags: list = None
    ):
        """Register a tool with the registry."""
        definition = ToolDefinition(
            tool=tool,
            domain=domain,
            handler=handler,
            description=description or tool.description,
            requires_auth=requires_auth,
            rate_limit=rate_limit,
            cache_ttl=cache_ttl,
            tags=tags or []
        )

        self._tools[name] = definition
        self._domain_index[domain].append(name)

        logger.debug(f"Registered tool: {name}", domain=domain.value)

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get tool handler by name."""
        definition = self._tools.get(name)
        return definition.handler if definition else None

    def get_tools_by_domain(self, domain: ToolDomain) -> list[Tool]:
        """Get all tools in a domain."""
        return [self._tools[name].tool for name in self._domain_index[domain]]

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return [d.tool for d in self._tools.values()]

    def list_tool_names(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.keys())

    def get_domain_stats(self) -> dict:
        """Get statistics by domain."""
        return {
            domain.value: len(tools)
            for domain, tools in self._domain_index.items()
        }

    async def call(self, name: str, arguments: dict) -> Any:
        """Call a tool by name with arguments."""
        definition = self._tools.get(name)

        if not definition:
            return {"error": f"Unknown tool: {name}"}

        try:
            result = await definition.handler(name, arguments)
            return result
        except Exception as e:
            logger.error(f"Tool call error: {name}", error=str(e))
            return {"error": str(e)}


# Global registry instance
registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return registry
