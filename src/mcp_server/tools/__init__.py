"""
MCP Tools Package for C1 Travel Agent System.
Exports all tool definitions and handlers.
"""
from .registry import ToolRegistry, ToolDomain, get_registry
from .flight_handlers import FLIGHT_TOOLS, handle_flight_tool
from .booking_handlers import BOOKING_TOOLS, handle_booking_tool
from .ticketing_handlers import TICKETING_TOOLS, handle_ticketing_tool
from .pnr_handlers import PNR_TOOLS, handle_pnr_tool
from .ancillary_handlers import ANCILLARY_TOOLS, handle_ancillary_tool
from .utility_handlers import UTILITY_TOOLS, handle_utility_tool

__all__ = [
    "ToolRegistry",
    "ToolDomain",
    "get_registry",
    "FLIGHT_TOOLS",
    "BOOKING_TOOLS",
    "TICKETING_TOOLS",
    "PNR_TOOLS",
    "ANCILLARY_TOOLS",
    "UTILITY_TOOLS",
    "handle_flight_tool",
    "handle_booking_tool",
    "handle_ticketing_tool",
    "handle_pnr_tool",
    "handle_ancillary_tool",
    "handle_utility_tool",
    "register_all_tools"
]


def register_all_tools():
    """Register all tools with the global registry."""
    registry = get_registry()

    # Register Flight Search tools (5)
    for name, tool in FLIGHT_TOOLS.items():
        registry.register(
            name=name,
            tool=tool,
            handler=handle_flight_tool,
            domain=ToolDomain.FLIGHT_SEARCH,
            cache_ttl=300  # 5 min cache for search results
        )

    # Register Booking tools (2)
    for name, tool in BOOKING_TOOLS.items():
        registry.register(
            name=name,
            tool=tool,
            handler=handle_booking_tool,
            domain=ToolDomain.BOOKING,
            requires_auth=True
        )

    # Register Ticketing tools (6)
    for name, tool in TICKETING_TOOLS.items():
        registry.register(
            name=name,
            tool=tool,
            handler=handle_ticketing_tool,
            domain=ToolDomain.TICKETING,
            requires_auth=True
        )

    # Register PNR tools (13)
    for name, tool in PNR_TOOLS.items():
        registry.register(
            name=name,
            tool=tool,
            handler=handle_pnr_tool,
            domain=ToolDomain.PNR_MANAGEMENT,
            requires_auth=True
        )

    # Register Ancillary tools (6)
    for name, tool in ANCILLARY_TOOLS.items():
        registry.register(
            name=name,
            tool=tool,
            handler=handle_ancillary_tool,
            domain=ToolDomain.ANCILLARY,
            requires_auth=True
        )

    # Register Utility tools (4)
    for name, tool in UTILITY_TOOLS.items():
        registry.register(
            name=name,
            tool=tool,
            handler=handle_utility_tool,
            domain=ToolDomain.UTILITY,
            cache_ttl=3600  # 1 hour cache for static data
        )

    return registry
