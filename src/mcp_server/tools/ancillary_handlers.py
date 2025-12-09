"""
MCP Ancillary Tool Handlers for C1 Travel Agent System.
Handles seats, baggage, meals, insurance.
"""
from typing import Any
import structlog
from mcp.types import Tool

from ..api_client.sftech import SFTechClient

logger = structlog.get_logger()

# Ancillary Tools (6 APIs)
ANCILLARY_TOOLS: dict[str, Tool] = {
    "get_seat_map": Tool(
        name="get_seat_map",
        description="Get seat map/availability for a flight segment",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "segment_index": {
                    "type": "integer",
                    "description": "Flight segment index (0-based)"
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "segment_index"]
        }
    ),
    "select_seat": Tool(
        name="select_seat",
        description="Select/assign seat for passenger",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "passenger_index": {"type": "integer"},
                "segment_index": {"type": "integer"},
                "seat_number": {
                    "type": "string",
                    "description": "Seat number like 12A, 15C"
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "passenger_index", "segment_index", "seat_number"]
        }
    ),
    "get_baggage_options": Tool(
        name="get_baggage_options",
        description="Get available baggage options and prices",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "segment_index": {"type": "integer"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code"]
        }
    ),
    "add_baggage": Tool(
        name="add_baggage",
        description="Add extra baggage allowance to booking",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "passenger_index": {"type": "integer"},
                "segment_index": {"type": "integer"},
                "baggage_code": {
                    "type": "string",
                    "description": "Baggage option code (e.g., BAG20, BAG30)"
                },
                "weight_kg": {
                    "type": "integer",
                    "description": "Baggage weight in kg"
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "passenger_index", "baggage_code"]
        }
    ),
    "get_meal_options": Tool(
        name="get_meal_options",
        description="Get available special meal options",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "segment_index": {"type": "integer"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code"]
        }
    ),
    "add_special_meal": Tool(
        name="add_special_meal",
        description="Add special meal request for passenger",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "passenger_index": {"type": "integer"},
                "segment_index": {"type": "integer"},
                "meal_code": {
                    "type": "string",
                    "description": "Meal code: VGML, AVML, HNML, DBML, etc."
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "passenger_index", "meal_code"]
        }
    )
}


async def handle_ancillary_tool(name: str, arguments: dict) -> dict:
    """Handle ancillary tool calls."""
    source = arguments.get("source", "VNA")
    client = SFTechClient(source=source)

    try:
        if name == "get_seat_map":
            result = await client.get_seat_map(
                booking_code=arguments["booking_code"],
                segment_index=arguments["segment_index"]
            )
            return {
                "success": True,
                "booking_code": arguments["booking_code"],
                "segment_index": arguments["segment_index"],
                "aircraft_type": result.get("aircraft_type"),
                "cabin_class": result.get("cabin_class"),
                "rows": result.get("rows", []),
                "available_seats": result.get("available_seats", []),
                "seat_prices": result.get("seat_prices", {})
            }

        elif name == "select_seat":
            result = await client.select_seat(
                booking_code=arguments["booking_code"],
                passenger_index=arguments["passenger_index"],
                segment_index=arguments["segment_index"],
                seat_number=arguments["seat_number"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "seat_number": arguments["seat_number"],
                "price": result.get("price", 0),
                "currency": result.get("currency", "VND"),
                "message": result.get("message")
            }

        elif name == "get_baggage_options":
            result = await client.get_baggage_options(
                booking_code=arguments["booking_code"],
                segment_index=arguments.get("segment_index")
            )
            return {
                "success": True,
                "booking_code": arguments["booking_code"],
                "options": result.get("options", []),
                "included_allowance": result.get("included_allowance"),
                "currency": result.get("currency", "VND")
            }

        elif name == "add_baggage":
            result = await client.add_baggage(
                booking_code=arguments["booking_code"],
                passenger_index=arguments["passenger_index"],
                segment_index=arguments.get("segment_index"),
                baggage_code=arguments["baggage_code"],
                weight_kg=arguments.get("weight_kg")
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "baggage_code": arguments["baggage_code"],
                "price": result.get("price", 0),
                "currency": result.get("currency", "VND"),
                "message": result.get("message")
            }

        elif name == "get_meal_options":
            result = await client.get_meal_options(
                booking_code=arguments["booking_code"],
                segment_index=arguments.get("segment_index")
            )
            return {
                "success": True,
                "booking_code": arguments["booking_code"],
                "options": result.get("options", [
                    {"code": "VGML", "name": "Vegetarian Meal", "description": "No meat"},
                    {"code": "AVML", "name": "Asian Vegetarian", "description": "Indian style"},
                    {"code": "HNML", "name": "Hindu Meal", "description": "No beef"},
                    {"code": "MOML", "name": "Muslim Meal", "description": "Halal"},
                    {"code": "DBML", "name": "Diabetic Meal", "description": "Low sugar"},
                    {"code": "GFML", "name": "Gluten Free", "description": "No gluten"},
                    {"code": "KSML", "name": "Kosher Meal", "description": "Kosher"},
                    {"code": "CHML", "name": "Child Meal", "description": "For children"}
                ])
            }

        elif name == "add_special_meal":
            result = await client.add_special_meal(
                booking_code=arguments["booking_code"],
                passenger_index=arguments["passenger_index"],
                segment_index=arguments.get("segment_index"),
                meal_code=arguments["meal_code"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "meal_code": arguments["meal_code"],
                "passenger_index": arguments["passenger_index"],
                "message": result.get("message", "Special meal request added")
            }

        else:
            return {"error": f"Unknown ancillary tool: {name}"}

    except Exception as e:
        logger.error(f"Ancillary tool error: {e}")
        return {"error": str(e)}
    finally:
        await client.close()
