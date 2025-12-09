"""
MCP Flight Tool Handlers for C1 Travel Agent System.
Defines tool schemas and handlers using MCP SDK 1.0+ API.
"""
from typing import Any
import structlog
from mcp.types import Tool

from ..api_client.sftech import SFTechClient

logger = structlog.get_logger()

# Tool definitions using MCP SDK Tool type
FLIGHT_TOOLS: dict[str, Tool] = {
    "search_oneway_flights": Tool(
        name="search_oneway_flights",
        description="Search for one-way flights between two airports",
        inputSchema={
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin airport code (e.g., SGN, HAN, DAD)"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination airport code"
                },
                "departure_date": {
                    "type": "string",
                    "description": "Departure date in YYYY-MM-DD format"
                },
                "adults": {
                    "type": "integer",
                    "description": "Number of adult passengers",
                    "default": 1
                },
                "children": {
                    "type": "integer",
                    "description": "Number of child passengers",
                    "default": 0
                },
                "infants": {
                    "type": "integer",
                    "description": "Number of infant passengers",
                    "default": 0
                },
                "cabin_class": {
                    "type": "string",
                    "description": "Cabin class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST",
                    "default": "ECONOMY"
                }
            },
            "required": ["origin", "destination", "departure_date"]
        }
    ),
    "search_roundtrip_flights": Tool(
        name="search_roundtrip_flights",
        description="Search for roundtrip flights between two airports",
        inputSchema={
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin airport code"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination airport code"
                },
                "departure_date": {
                    "type": "string",
                    "description": "Outbound departure date (YYYY-MM-DD)"
                },
                "return_date": {
                    "type": "string",
                    "description": "Return date (YYYY-MM-DD)"
                },
                "adults": {"type": "integer", "default": 1},
                "children": {"type": "integer", "default": 0},
                "infants": {"type": "integer", "default": 0},
                "cabin_class": {"type": "string", "default": "ECONOMY"}
            },
            "required": ["origin", "destination", "departure_date", "return_date"]
        }
    ),
    "search_multicity_flights": Tool(
        name="search_multicity_flights",
        description="Search for multi-city flights with multiple legs",
        inputSchema={
            "type": "object",
            "properties": {
                "legs": {
                    "type": "array",
                    "description": "List of flight legs with origin, destination, departure_date",
                    "items": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string"},
                            "destination": {"type": "string"},
                            "departure_date": {"type": "string"}
                        },
                        "required": ["origin", "destination", "departure_date"]
                    }
                },
                "adults": {"type": "integer", "default": 1},
                "children": {"type": "integer", "default": 0},
                "infants": {"type": "integer", "default": 0},
                "cabin_class": {"type": "string", "default": "ECONOMY"}
            },
            "required": ["legs"]
        }
    ),
    "get_flight_details": Tool(
        name="get_flight_details",
        description="Get detailed information about a specific flight",
        inputSchema={
            "type": "object",
            "properties": {
                "flight_number": {
                    "type": "string",
                    "description": "Flight number (e.g., QH202, VN123)"
                },
                "origin": {"type": "string"},
                "destination": {"type": "string"},
                "departure_date": {"type": "string"},
                "gds_source": {
                    "type": "string",
                    "description": "GDS source - QH recommended",
                    "default": "QH"
                }
            },
            "required": ["flight_number", "origin", "destination", "departure_date"]
        }
    ),
    "get_fare_rules": Tool(
        name="get_fare_rules",
        description="Get fare rules for a specific flight from search results",
        inputSchema={
            "type": "object",
            "properties": {
                "search_id": {"type": "string", "description": "Search ID from flight search"},
                "flight_id": {"type": "string", "description": "Flight ID from results"}
            },
            "required": ["search_id", "flight_id"]
        }
    )
}


async def handle_flight_tool(name: str, arguments: dict) -> dict:
    """Handle flight tool calls."""
    client = SFTechClient(source="F1")

    try:
        if name == "search_oneway_flights":
            result = await client.search_oneway_flights(
                origin=arguments["origin"],
                destination=arguments["destination"],
                departure_date=arguments["departure_date"],
                adults=arguments.get("adults", 1),
                children=arguments.get("children", 0),
                infants=arguments.get("infants", 0),
                cabin_class=arguments.get("cabin_class", "ECONOMY")
            )
            return _format_search_result(result)

        elif name == "search_roundtrip_flights":
            result = await client.search_roundtrip_flights(
                origin=arguments["origin"],
                destination=arguments["destination"],
                departure_date=arguments["departure_date"],
                return_date=arguments["return_date"],
                adults=arguments.get("adults", 1),
                children=arguments.get("children", 0),
                infants=arguments.get("infants", 0),
                cabin_class=arguments.get("cabin_class", "ECONOMY")
            )
            return _format_search_result(result)

        elif name == "search_multicity_flights":
            result = await client.search_multicity_flights(
                legs=arguments["legs"],
                adults=arguments.get("adults", 1),
                children=arguments.get("children", 0),
                infants=arguments.get("infants", 0),
                cabin_class=arguments.get("cabin_class", "ECONOMY")
            )
            return _format_search_result(result)

        elif name == "get_flight_details":
            result = await client.get_flight_details(
                flight_number=arguments["flight_number"],
                origin=arguments["origin"],
                destination=arguments["destination"],
                departure_date=arguments["departure_date"],
                gds_source=arguments.get("gds_source", "QH")
            )
            return {
                "flight_number": result.flight_number,
                "airline": result.airline,
                "origin": result.origin,
                "destination": result.destination,
                "departure_date": result.departure_date,
                "departure_time": result.departure_time,
                "arrival_time": result.arrival_time,
                "duration": result.duration,
                "aircraft": result.aircraft,
                "status": result.status,
                "fare_classes": result.fare_classes,
                "amenities": result.amenities
            }

        elif name == "get_fare_rules":
            result = await client.get_fare_rules(
                search_id=arguments["search_id"],
                flight_id=arguments["flight_id"]
            )
            return result

        else:
            return {"error": f"Unknown flight tool: {name}"}

    except Exception as e:
        logger.error(f"Flight tool error: {e}")
        return {"error": str(e)}
    finally:
        await client.close()


def _format_search_result(result) -> dict:
    """Format flight search result to dict."""
    return {
        "search_id": result.search_id,
        "total_results": result.total_results,
        "has_more": result.has_more,
        "flights": [
            {
                "id": f.id,
                "source": f.source,
                "total_price": f.total_price,
                "currency": f.currency,
                "cabin_class": f.cabin_class,
                "segments": [
                    {
                        "flight_number": s.flight_number,
                        "airline": s.airline,
                        "origin": s.origin,
                        "destination": s.destination,
                        "departure_time": s.departure_time,
                        "arrival_time": s.arrival_time,
                        "duration": s.duration
                    }
                    for s in f.segments
                ]
            }
            for f in result.flights[:20]
        ]
    }
