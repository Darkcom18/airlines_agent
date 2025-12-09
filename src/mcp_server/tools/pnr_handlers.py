"""
MCP PNR Management Tool Handlers for C1 Travel Agent System.
Handles PNR retrieval, modification, split, remarks.
"""
from typing import Any
import structlog
from mcp.types import Tool

from ..api_client.sftech import SFTechClient

logger = structlog.get_logger()

# PNR Management Tools (13 APIs)
PNR_TOOLS: dict[str, Tool] = {
    "retrieve_pnr": Tool(
        name="retrieve_pnr",
        description="Retrieve PNR details by booking code",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {
                    "type": "string",
                    "description": "6-character PNR/Booking code"
                },
                "source": {"type": "string", "default": "VNA"},
                "last_name": {
                    "type": "string",
                    "description": "Passenger last name for verification"
                }
            },
            "required": ["booking_code"]
        }
    ),
    "cancel_pnr": Tool(
        name="cancel_pnr",
        description="Cancel entire PNR/booking",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "source": {"type": "string", "default": "VNA"},
                "reason": {"type": "string"}
            },
            "required": ["booking_code"]
        }
    ),
    "cancel_segment": Tool(
        name="cancel_segment",
        description="Cancel specific flight segment in PNR",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "segment_index": {
                    "type": "integer",
                    "description": "Segment index to cancel (0-based)"
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "segment_index"]
        }
    ),
    "change_flight": Tool(
        name="change_flight",
        description="Change flight in existing PNR to new flight",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "segment_index": {"type": "integer"},
                "new_flight_id": {
                    "type": "string",
                    "description": "New flight ID from search results"
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "segment_index", "new_flight_id"]
        }
    ),
    "add_passenger": Tool(
        name="add_passenger",
        description="Add passenger to existing PNR",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "passenger": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "date_of_birth": {"type": "string"}
                    },
                    "required": ["type", "title", "first_name", "last_name"]
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "passenger"]
        }
    ),
    "remove_passenger": Tool(
        name="remove_passenger",
        description="Remove passenger from PNR",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "passenger_index": {"type": "integer"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "passenger_index"]
        }
    ),
    "split_pnr": Tool(
        name="split_pnr",
        description="Split PNR into separate bookings by passenger",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "passenger_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Passenger indices to split into new PNR"
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "passenger_indices"]
        }
    ),
    "update_contact": Tool(
        name="update_contact",
        description="Update contact information in PNR",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code"]
        }
    ),
    "add_ssr": Tool(
        name="add_ssr",
        description="Add Special Service Request (SSR) to PNR",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "ssr_code": {
                    "type": "string",
                    "description": "SSR code: WCHR, MEAL, BLND, etc."
                },
                "passenger_index": {"type": "integer"},
                "segment_index": {"type": "integer"},
                "free_text": {"type": "string"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "ssr_code"]
        }
    ),
    "add_osi": Tool(
        name="add_osi",
        description="Add Other Service Information (OSI) remark",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "airline_code": {"type": "string"},
                "text": {"type": "string", "description": "OSI text"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "airline_code", "text"]
        }
    ),
    "add_remark": Tool(
        name="add_remark",
        description="Add general remark to PNR",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "remark_type": {
                    "type": "string",
                    "description": "GENERAL, ITINERARY, INVOICE, etc."
                },
                "text": {"type": "string"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "text"]
        }
    ),
    "add_frequent_flyer": Tool(
        name="add_frequent_flyer",
        description="Add frequent flyer number to passenger",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "passenger_index": {"type": "integer"},
                "airline_code": {"type": "string"},
                "ff_number": {"type": "string"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "passenger_index", "airline_code", "ff_number"]
        }
    ),
    "get_pnr_history": Tool(
        name="get_pnr_history",
        description="Get PNR history/changelog",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code"]
        }
    )
}


async def handle_pnr_tool(name: str, arguments: dict) -> dict:
    """Handle PNR management tool calls."""
    source = arguments.get("source", "VNA")
    client = SFTechClient(source=source)

    try:
        if name == "retrieve_pnr":
            result = await client.retrieve_pnr(
                booking_code=arguments["booking_code"],
                last_name=arguments.get("last_name")
            )
            return {
                "success": True,
                "booking_code": arguments["booking_code"],
                "status": result.get("status"),
                "passengers": result.get("passengers", []),
                "segments": result.get("segments", []),
                "contact": result.get("contact"),
                "tickets": result.get("tickets", []),
                "remarks": result.get("remarks", []),
                "time_limit": result.get("time_limit")
            }

        elif name == "cancel_pnr":
            result = await client.cancel_pnr(
                booking_code=arguments["booking_code"],
                reason=arguments.get("reason", "Customer request")
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "status": "CANCELLED" if result.get("success") else "FAILED",
                "message": result.get("message")
            }

        elif name == "cancel_segment":
            result = await client.cancel_segment(
                booking_code=arguments["booking_code"],
                segment_index=arguments["segment_index"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "cancelled_segment": arguments["segment_index"],
                "message": result.get("message")
            }

        elif name == "change_flight":
            result = await client.change_flight(
                booking_code=arguments["booking_code"],
                segment_index=arguments["segment_index"],
                new_flight_id=arguments["new_flight_id"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "new_segment": result.get("new_segment"),
                "fare_difference": result.get("fare_difference", 0),
                "message": result.get("message")
            }

        elif name == "add_passenger":
            result = await client.add_passenger(
                booking_code=arguments["booking_code"],
                passenger=arguments["passenger"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "passenger_index": result.get("passenger_index"),
                "additional_fare": result.get("additional_fare", 0),
                "message": result.get("message")
            }

        elif name == "remove_passenger":
            result = await client.remove_passenger(
                booking_code=arguments["booking_code"],
                passenger_index=arguments["passenger_index"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "removed_passenger": arguments["passenger_index"],
                "message": result.get("message")
            }

        elif name == "split_pnr":
            result = await client.split_pnr(
                booking_code=arguments["booking_code"],
                passenger_indices=arguments["passenger_indices"]
            )
            return {
                "success": result.get("success", False),
                "original_pnr": arguments["booking_code"],
                "new_pnr": result.get("new_pnr"),
                "message": result.get("message")
            }

        elif name == "update_contact":
            result = await client.update_contact(
                booking_code=arguments["booking_code"],
                email=arguments.get("email"),
                phone=arguments.get("phone")
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "message": result.get("message")
            }

        elif name == "add_ssr":
            result = await client.add_ssr(
                booking_code=arguments["booking_code"],
                ssr_code=arguments["ssr_code"],
                passenger_index=arguments.get("passenger_index"),
                segment_index=arguments.get("segment_index"),
                free_text=arguments.get("free_text")
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "ssr_code": arguments["ssr_code"],
                "message": result.get("message")
            }

        elif name == "add_osi":
            result = await client.add_osi(
                booking_code=arguments["booking_code"],
                airline_code=arguments["airline_code"],
                text=arguments["text"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "message": result.get("message")
            }

        elif name == "add_remark":
            result = await client.add_remark(
                booking_code=arguments["booking_code"],
                remark_type=arguments.get("remark_type", "GENERAL"),
                text=arguments["text"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "message": result.get("message")
            }

        elif name == "add_frequent_flyer":
            result = await client.add_frequent_flyer(
                booking_code=arguments["booking_code"],
                passenger_index=arguments["passenger_index"],
                airline_code=arguments["airline_code"],
                ff_number=arguments["ff_number"]
            )
            return {
                "success": result.get("success", False),
                "booking_code": arguments["booking_code"],
                "message": result.get("message")
            }

        elif name == "get_pnr_history":
            result = await client.get_pnr_history_log(
                booking_code=arguments["booking_code"]
            )
            return {
                "booking_code": arguments["booking_code"],
                "history": result.get("history", []),
                "created_at": result.get("created_at"),
                "last_modified": result.get("last_modified")
            }

        else:
            return {"error": f"Unknown PNR tool: {name}"}

    except Exception as e:
        logger.error(f"PNR tool error: {e}")
        return {"error": str(e)}
    finally:
        await client.close()
