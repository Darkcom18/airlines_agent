"""
MCP Booking Tool Handlers for C1 Travel Agent System.
Defines tool schemas and handlers using MCP SDK 1.0+ API.
"""
from typing import Any, Optional
import structlog
from mcp.types import Tool

from ..api_client.sftech import SFTechClient

logger = structlog.get_logger()

# Tool definitions using MCP SDK Tool type
BOOKING_TOOLS: dict[str, Tool] = {
    "hold_booking": Tool(
        name="hold_booking",
        description="Create a booking hold for selected flight",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "GDS source - VNA, QH, or VJ"
                },
                "passengers": {
                    "type": "array",
                    "description": "List of passenger information",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "ADT (adult), CHD (child), or INF (infant)"
                            },
                            "title": {
                                "type": "string",
                                "description": "Mr, Mrs, Ms, etc."
                            },
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "date_of_birth": {
                                "type": "string",
                                "description": "YYYY-MM-DD, required for children/infants"
                            }
                        },
                        "required": ["type", "title", "first_name", "last_name"]
                    }
                },
                "contact": {
                    "type": "object",
                    "description": "Contact information",
                    "properties": {
                        "email": {"type": "string"},
                        "phone": {"type": "string"}
                    },
                    "required": ["email", "phone"]
                },
                "search_id": {"type": "string"},
                "flight_id": {"type": "string"}
            },
            "required": ["source", "passengers", "contact"]
        }
    ),
    "get_booking_history": Tool(
        name="get_booking_history",
        description="Retrieve booking/PNR history and details",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {
                    "type": "string",
                    "description": "PNR or booking confirmation code"
                },
                "source": {
                    "type": "string",
                    "description": "GDS source - VNA, QH, or VJ",
                    "default": "VNA"
                },
                "last_name": {
                    "type": "string",
                    "description": "Passenger last name for verification"
                }
            },
            "required": ["booking_code"]
        }
    )
}


async def handle_booking_tool(name: str, arguments: dict) -> dict:
    """Handle booking tool calls."""
    client = SFTechClient(source="F1")

    try:
        if name == "hold_booking":
            result = await client.hold_booking(
                source=arguments["source"],
                passengers=arguments["passengers"],
                contact=arguments["contact"],
                search_id=arguments.get("search_id"),
                flight_id=arguments.get("flight_id")
            )
            return {
                "success": result.success,
                "booking_code": result.booking_code,
                "status": result.status,
                "message": result.message,
                "total_price": result.total_price,
                "currency": result.currency,
                "time_limit": result.time_limit
            }

        elif name == "get_booking_history":
            result = await client.get_pnr_history(
                booking_code=arguments["booking_code"],
                source=arguments.get("source", "VNA"),
                last_name=arguments.get("last_name")
            )
            return {
                "success": result.success,
                "booking_code": result.booking_code,
                "status": result.status,
                "passengers": result.passengers,
                "flights": result.flights,
                "contact": result.contact,
                "price_info": result.price_info
            }

        else:
            return {"error": f"Unknown booking tool: {name}"}

    except Exception as e:
        logger.error(f"Booking tool error: {e}")
        return {"error": str(e)}
    finally:
        await client.close()
