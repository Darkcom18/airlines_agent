"""
MCP Tools for Booking operations.
"""
from typing import Any, Optional

import structlog

from ..api_client.sftech import SFTechClient

logger = structlog.get_logger()


def register_booking_tools(mcp_server):
    """Register booking tools with MCP server."""

    @mcp_server.tool()
    async def hold_booking(
        source: str,
        passengers: list[dict],
        contact: dict,
        search_id: Optional[str] = None,
        flight_id: Optional[str] = None
    ) -> dict:
        """
        Create a booking hold for selected flight.

        Args:
            source: GDS source - VNA, QH, or VJ
            passengers: List of passenger information. Each passenger must have:
                       - type: ADT (adult), CHD (child), or INF (infant)
                       - title: Mr, Mrs, Ms, etc.
                       - first_name: Passenger first name
                       - last_name: Passenger last name
                       - date_of_birth: Date of birth (YYYY-MM-DD) - required for children/infants
            contact: Contact information with:
                    - email: Contact email
                    - phone: Contact phone number
            search_id: Search ID from flight search
            flight_id: Flight ID from search results

        Returns:
            Booking response with PNR code and status

        Example:
            passengers = [
                {
                    "type": "ADT",
                    "title": "Mr",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            ]
            contact = {
                "email": "john@example.com",
                "phone": "+84901234567"
            }
        """
        logger.info(
            "MCP Tool: hold_booking",
            source=source,
            num_passengers=len(passengers)
        )

        client = SFTechClient(source="F1")
        try:
            result = await client.hold_booking(
                source=source,
                passengers=passengers,
                contact=contact,
                search_id=search_id,
                flight_id=flight_id
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
        finally:
            await client.close()

    @mcp_server.tool()
    async def get_booking_history(
        booking_code: str,
        source: str = "VNA",
        last_name: Optional[str] = None
    ) -> dict:
        """
        Retrieve booking/PNR history and details.

        Args:
            booking_code: PNR or booking confirmation code
            source: GDS source - VNA, QH, or VJ (default: VNA)
            last_name: Passenger last name for verification (optional)

        Returns:
            Booking details including passengers, flights, and status
        """
        logger.info(
            "MCP Tool: get_booking_history",
            booking_code=booking_code,
            source=source
        )

        client = SFTechClient(source="F1")
        try:
            result = await client.get_pnr_history(
                booking_code=booking_code,
                source=source,
                last_name=last_name
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
        finally:
            await client.close()

    logger.info("Booking tools registered with MCP server")
