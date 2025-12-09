"""
MCP Tools for Flight Search operations.
"""
from typing import Any

import structlog

from ..api_client.sftech import SFTechClient

logger = structlog.get_logger()


def register_flight_tools(mcp_server):
    """Register flight search tools with MCP server."""

    @mcp_server.tool()
    async def search_oneway_flights(
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "ECONOMY"
    ) -> dict:
        """
        Search for one-way flights.

        Args:
            origin: Origin airport code (e.g., DAD, SGN, HAN)
            destination: Destination airport code
            departure_date: Departure date in YYYY-MM-DD format
            adults: Number of adult passengers (default: 1)
            children: Number of child passengers (default: 0)
            infants: Number of infant passengers (default: 0)
            cabin_class: Cabin class - ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST (default: ECONOMY)

        Returns:
            Dictionary with search_id, flights list, and total_results
        """
        logger.info(
            "MCP Tool: search_oneway_flights",
            origin=origin,
            destination=destination,
            date=departure_date
        )

        client = SFTechClient(source="F1")
        try:
            result = await client.search_oneway_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class
            )

            # Convert to dict for MCP response
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
                    for f in result.flights[:20]  # Limit for readability
                ]
            }
        finally:
            await client.close()

    @mcp_server.tool()
    async def search_roundtrip_flights(
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "ECONOMY"
    ) -> dict:
        """
        Search for roundtrip flights.

        Args:
            origin: Origin airport code (e.g., DAD, SGN, HAN)
            destination: Destination airport code
            departure_date: Outbound departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format
            adults: Number of adult passengers (default: 1)
            children: Number of child passengers (default: 0)
            infants: Number of infant passengers (default: 0)
            cabin_class: Cabin class - ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST (default: ECONOMY)

        Returns:
            Dictionary with search_id, flights list, and total_results
        """
        logger.info(
            "MCP Tool: search_roundtrip_flights",
            origin=origin,
            destination=destination,
            departure=departure_date,
            return_date=return_date
        )

        client = SFTechClient(source="F1")
        try:
            result = await client.search_roundtrip_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class
            )

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
        finally:
            await client.close()

    @mcp_server.tool()
    async def search_multicity_flights(
        legs: list[dict],
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "ECONOMY"
    ) -> dict:
        """
        Search for multi-city flights.

        Args:
            legs: List of flight legs. Each leg must have:
                  - origin: Origin airport code
                  - destination: Destination airport code
                  - departure_date: Departure date (YYYY-MM-DD)
            adults: Number of adult passengers (default: 1)
            children: Number of child passengers (default: 0)
            infants: Number of infant passengers (default: 0)
            cabin_class: Cabin class (default: ECONOMY)

        Returns:
            Dictionary with search_id, flights list, and total_results

        Example legs:
            [
                {"origin": "SGN", "destination": "HAN", "departure_date": "2025-01-15"},
                {"origin": "HAN", "destination": "DAD", "departure_date": "2025-01-18"}
            ]
        """
        logger.info("MCP Tool: search_multicity_flights", legs=legs)

        client = SFTechClient(source="F1")
        try:
            result = await client.search_multicity_flights(
                legs=legs,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class
            )

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
        finally:
            await client.close()

    @mcp_server.tool()
    async def load_more_flight_results(
        search_type: str,
        search_id: str,
        page: int = 2
    ) -> dict:
        """
        Load more flight results from a previous search.

        Args:
            search_type: Type of search - oneway, roundtrip, or multicity
            search_id: Search ID from the previous search response
            page: Page number to load (default: 2)

        Returns:
            Dictionary with additional flights
        """
        logger.info(
            "MCP Tool: load_more_flight_results",
            search_type=search_type,
            search_id=search_id,
            page=page
        )

        client = SFTechClient(source="F1")
        try:
            result = await client.load_more_flights(
                search_type=search_type,
                search_id=search_id,
                page=page
            )

            return {
                "search_id": result.search_id,
                "total_results": result.total_results,
                "has_more": result.has_more,
                "page": page,
                "flights": [
                    {
                        "id": f.id,
                        "source": f.source,
                        "total_price": f.total_price,
                        "currency": f.currency,
                        "segments": [
                            {
                                "flight_number": s.flight_number,
                                "airline": s.airline,
                                "origin": s.origin,
                                "destination": s.destination,
                                "departure_time": s.departure_time,
                                "arrival_time": s.arrival_time
                            }
                            for s in f.segments
                        ]
                    }
                    for f in result.flights
                ]
            }
        finally:
            await client.close()

    @mcp_server.tool()
    async def get_flight_details(
        flight_number: str,
        origin: str,
        destination: str,
        departure_date: str,
        gds_source: str = "QH"
    ) -> dict:
        """
        Get detailed information about a specific flight.

        Note: Currently only works with QH (Bamboo Airways).
        VNA and SABRE return "not implemented".

        Args:
            flight_number: Flight number (e.g., QH202, VN123)
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Departure date in YYYY-MM-DD format
            gds_source: GDS source - QH recommended (default: QH)

        Returns:
            Detailed flight information including schedule, aircraft, etc.
        """
        logger.info(
            "MCP Tool: get_flight_details",
            flight_number=flight_number,
            source=gds_source
        )

        client = SFTechClient(source="F1")
        try:
            result = await client.get_flight_details(
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                gds_source=gds_source
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
        finally:
            await client.close()

    @mcp_server.tool()
    async def get_fare_rules(
        search_id: str,
        flight_id: str
    ) -> dict:
        """
        Get fare rules for a specific flight from search results.

        Args:
            search_id: Search ID from flight search response
            flight_id: Flight ID from search results

        Returns:
            Fare rules including cancellation, change policies, baggage, etc.
        """
        logger.info(
            "MCP Tool: get_fare_rules",
            search_id=search_id,
            flight_id=flight_id
        )

        client = SFTechClient(source="F1")
        try:
            result = await client.get_fare_rules(
                search_id=search_id,
                flight_id=flight_id
            )
            return result
        finally:
            await client.close()

    logger.info("Flight tools registered with MCP server")
