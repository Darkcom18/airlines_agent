"""
MCP Ticketing Tool Handlers for C1 Travel Agent System.
Handles ticket issuance, EMD, void operations.
"""
from typing import Any
import structlog
from mcp.types import Tool

from ..api_client.sftech import SFTechClient

logger = structlog.get_logger()

# Ticketing Tools (6 APIs)
TICKETING_TOOLS: dict[str, Tool] = {
    "issue_ticket": Tool(
        name="issue_ticket",
        description="Issue e-ticket for a confirmed booking/PNR",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {
                    "type": "string",
                    "description": "PNR/Booking code to issue ticket for"
                },
                "source": {
                    "type": "string",
                    "description": "GDS source - VNA, QH, VJ",
                    "default": "VNA"
                },
                "payment_method": {
                    "type": "string",
                    "description": "Payment method: CASH, CREDIT, AGENT_CREDIT",
                    "default": "AGENT_CREDIT"
                }
            },
            "required": ["booking_code"]
        }
    ),
    "void_ticket": Tool(
        name="void_ticket",
        description="Void an issued ticket within 24 hours of issuance",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_number": {
                    "type": "string",
                    "description": "13-digit ticket number to void"
                },
                "booking_code": {
                    "type": "string",
                    "description": "PNR/Booking code"
                },
                "source": {
                    "type": "string",
                    "default": "VNA"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for voiding"
                }
            },
            "required": ["ticket_number", "booking_code"]
        }
    ),
    "reissue_ticket": Tool(
        name="reissue_ticket",
        description="Reissue ticket for date/route change with fare difference",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_number": {"type": "string"},
                "booking_code": {"type": "string"},
                "new_flight_id": {
                    "type": "string",
                    "description": "New flight selection from search"
                },
                "source": {"type": "string", "default": "VNA"},
                "fare_difference": {
                    "type": "number",
                    "description": "Additional fare to collect (if any)"
                }
            },
            "required": ["ticket_number", "booking_code", "new_flight_id"]
        }
    ),
    "issue_emd": Tool(
        name="issue_emd",
        description="Issue EMD (Electronic Miscellaneous Document) for ancillaries",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_code": {"type": "string"},
                "emd_type": {
                    "type": "string",
                    "description": "EMD type: BAGGAGE, SEAT, MEAL, INSURANCE"
                },
                "passenger_index": {
                    "type": "integer",
                    "description": "Passenger index (0-based)"
                },
                "segment_index": {
                    "type": "integer",
                    "description": "Flight segment index (0-based)"
                },
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["booking_code", "emd_type"]
        }
    ),
    "get_ticket_status": Tool(
        name="get_ticket_status",
        description="Get ticket status and details",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_number": {"type": "string"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["ticket_number"]
        }
    ),
    "refund_ticket": Tool(
        name="refund_ticket",
        description="Request refund for unused ticket",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_number": {"type": "string"},
                "booking_code": {"type": "string"},
                "refund_type": {
                    "type": "string",
                    "description": "VOLUNTARY or INVOLUNTARY",
                    "default": "VOLUNTARY"
                },
                "reason": {"type": "string"},
                "source": {"type": "string", "default": "VNA"}
            },
            "required": ["ticket_number", "booking_code"]
        }
    )
}


async def handle_ticketing_tool(name: str, arguments: dict) -> dict:
    """Handle ticketing tool calls."""
    source = arguments.get("source", "VNA")
    client = SFTechClient(source=source)

    try:
        if name == "issue_ticket":
            # Call SFTech ticketing API
            result = await client.issue_ticket(
                booking_code=arguments["booking_code"],
                payment_method=arguments.get("payment_method", "AGENT_CREDIT")
            )
            return {
                "success": result.get("success", False),
                "ticket_number": result.get("ticket_number"),
                "booking_code": arguments["booking_code"],
                "status": result.get("status", "ISSUED"),
                "message": result.get("message", "Ticket issued successfully"),
                "issued_at": result.get("issued_at")
            }

        elif name == "void_ticket":
            result = await client.void_ticket(
                ticket_number=arguments["ticket_number"],
                booking_code=arguments["booking_code"],
                reason=arguments.get("reason", "Customer request")
            )
            return {
                "success": result.get("success", False),
                "ticket_number": arguments["ticket_number"],
                "status": "VOIDED" if result.get("success") else "FAILED",
                "message": result.get("message")
            }

        elif name == "reissue_ticket":
            result = await client.reissue_ticket(
                ticket_number=arguments["ticket_number"],
                booking_code=arguments["booking_code"],
                new_flight_id=arguments["new_flight_id"],
                fare_difference=arguments.get("fare_difference", 0)
            )
            return {
                "success": result.get("success", False),
                "new_ticket_number": result.get("new_ticket_number"),
                "fare_difference": result.get("fare_difference", 0),
                "message": result.get("message")
            }

        elif name == "issue_emd":
            result = await client.issue_emd(
                booking_code=arguments["booking_code"],
                emd_type=arguments["emd_type"],
                passenger_index=arguments.get("passenger_index", 0),
                segment_index=arguments.get("segment_index", 0)
            )
            return {
                "success": result.get("success", False),
                "emd_number": result.get("emd_number"),
                "emd_type": arguments["emd_type"],
                "amount": result.get("amount", 0),
                "message": result.get("message")
            }

        elif name == "get_ticket_status":
            result = await client.get_ticket_status(
                ticket_number=arguments["ticket_number"]
            )
            return {
                "ticket_number": arguments["ticket_number"],
                "status": result.get("status", "UNKNOWN"),
                "issued_date": result.get("issued_date"),
                "passenger_name": result.get("passenger_name"),
                "flight_info": result.get("flight_info"),
                "fare_info": result.get("fare_info")
            }

        elif name == "refund_ticket":
            result = await client.refund_ticket(
                ticket_number=arguments["ticket_number"],
                booking_code=arguments["booking_code"],
                refund_type=arguments.get("refund_type", "VOLUNTARY"),
                reason=arguments.get("reason")
            )
            return {
                "success": result.get("success", False),
                "ticket_number": arguments["ticket_number"],
                "refund_amount": result.get("refund_amount", 0),
                "penalty": result.get("penalty", 0),
                "status": result.get("status"),
                "message": result.get("message")
            }

        else:
            return {"error": f"Unknown ticketing tool: {name}"}

    except Exception as e:
        logger.error(f"Ticketing tool error: {e}")
        return {"error": str(e)}
    finally:
        await client.close()
