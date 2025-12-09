"""
SFTech API Client for flight search, details, and booking.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

import structlog

from config.settings import settings
from .base import BaseAPIClient, APIError
from .models import (
    FlightSearchRequest,
    FlightSearchResponse,
    FlightOption,
    FlightSegment,
    FlightDetails,
    BookingRequest,
    BookingResponse,
    PNRHistoryRequest,
    PNRHistoryResponse,
    CabinClass,
)

logger = structlog.get_logger()


class SFTechClient(BaseAPIClient):
    """Client for SFTech Travel APIs."""

    def __init__(self, source: str = "F1"):
        """
        Initialize SFTech client.

        Args:
            source: API source (F1, F10, VJ)
        """
        super().__init__(base_url=settings.sftech_api_base)
        self.source = source.upper()
        self._headers = settings.get_sftech_headers(self.source)

    def _get_headers(self) -> dict:
        """Get API headers."""
        return self._headers.copy()

    # ===========================================
    # Flight Search APIs
    # ===========================================

    async def search_oneway_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "ECONOMY"
    ) -> FlightSearchResponse:
        """
        Search for one-way flights.

        Args:
            origin: Origin airport code (e.g., DAD, SGN, HAN)
            destination: Destination airport code
            departure_date: Departure date (YYYY-MM-DD)
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class (ECONOMY, BUSINESS, etc.)

        Returns:
            FlightSearchResponse with list of flights
        """
        payload = {
            "workspaceId": 1,
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "children": children,
            "infants": infants,
            "cabinClass": cabin_class.upper(),
            "directOnly": False,
            "limit": 20,
            "sortBy": "PRICE",
            "sortOrder": "ASC"
        }

        log = logger.bind(
            action="search_oneway",
            origin=origin,
            destination=destination,
            date=departure_date
        )
        log.info("Searching one-way flights")

        response = await self.post(
            "/api/v1/flights/search/oneway",
            headers=self._get_headers(),
            json_data=payload
        )

        return self._parse_search_response(response, payload)

    async def search_roundtrip_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "ECONOMY"
    ) -> FlightSearchResponse:
        """
        Search for roundtrip flights.

        Args:
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Outbound departure date (YYYY-MM-DD)
            return_date: Return date (YYYY-MM-DD)
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class

        Returns:
            FlightSearchResponse with list of flights
        """
        payload = {
            "workspaceId": 1,
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": adults,
            "children": children,
            "infants": infants,
            "cabinClass": cabin_class.upper(),
            "directOnly": False,
            "limit": 20,
            "sortBy": "PRICE",
            "sortOrder": "ASC"
        }

        log = logger.bind(
            action="search_roundtrip",
            origin=origin,
            destination=destination,
            departure=departure_date,
            return_date=return_date
        )
        log.info("Searching roundtrip flights")

        response = await self.post(
            "/api/v1/flights/search/roundtrip",
            headers=self._get_headers(),
            json_data=payload
        )

        return self._parse_search_response(response, payload)

    async def search_multicity_flights(
        self,
        legs: list[dict],
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "ECONOMY"
    ) -> FlightSearchResponse:
        """
        Search for multi-city flights.

        Args:
            legs: List of flight legs, each with:
                  - origin: Origin airport code
                  - destination: Destination airport code
                  - departureDate: Departure date (YYYY-MM-DD)
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class

        Returns:
            FlightSearchResponse with list of flights
        """
        # Format routes for API
        routes = []
        for leg in legs:
            routes.append({
                "origin": leg["origin"].upper(),
                "destination": leg["destination"].upper(),
                "departureDate": leg.get("departureDate") or leg.get("departure_date")
            })

        payload = {
            "workspaceId": 1,
            "routes": routes,
            "adults": adults,
            "children": children,
            "infants": infants,
            "cabinClass": cabin_class.upper(),
            "directOnly": False,
            "limit": 10,
            "sortBy": "price",
            "sortOrder": "asc"
        }

        log = logger.bind(action="search_multicity", routes=routes)
        log.info("Searching multi-city flights")

        response = await self.post(
            "/api/v1/flights/search/multicity",
            headers=self._get_headers(),
            json_data=payload
        )

        return self._parse_search_response(response, payload)

    async def load_more_flights(
        self,
        search_type: str,
        search_id: str,
        page: int = 2
    ) -> FlightSearchResponse:
        """
        Load more flight results.

        Args:
            search_type: Type of search (oneway, roundtrip, multicity)
            search_id: Search ID from previous search
            page: Page number to load

        Returns:
            FlightSearchResponse with additional flights
        """
        payload = {
            "searchId": search_id,
            "page": page
        }

        endpoint = f"/api/v1/flights/search/{search_type}/load-more"

        log = logger.bind(
            action="load_more",
            search_type=search_type,
            search_id=search_id,
            page=page
        )
        log.info("Loading more flights")

        response = await self.post(
            endpoint,
            headers=self._get_headers(),
            json_data=payload
        )

        return self._parse_search_response(response, {"searchId": search_id})

    # ===========================================
    # Flight Details APIs
    # ===========================================

    async def get_flight_details(
        self,
        flight_number: str,
        origin: str,
        destination: str,
        departure_date: str,
        gds_source: str = "QH"
    ) -> FlightDetails:
        """
        Get detailed flight information.

        Note: Currently only works with QH (Bamboo Airways).
        VNA and SABRE return 501 "not implemented".

        Args:
            flight_number: Flight number (e.g., QH202)
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Departure date (YYYY-MM-DD)
            gds_source: GDS source (QH recommended)

        Returns:
            FlightDetails with detailed flight info
        """
        payload = {
            "source": gds_source.upper(),
            "flightNumber": flight_number,
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departureDate": departure_date
        }

        log = logger.bind(
            action="get_flight_details",
            flight_number=flight_number,
            source=gds_source
        )
        log.info("Getting flight details")

        response = await self.post(
            "/api/v1/flights/details",
            headers=self._get_headers(),
            json_data=payload
        )

        return self._parse_flight_details(response)

    async def get_fare_rules(
        self,
        search_id: str,
        flight_id: str,
        verify_session: Optional[str] = None
    ) -> dict:
        """
        Get fare rules for a flight.

        Args:
            search_id: Search ID from flight search
            flight_id: Flight ID from search results
            verify_session: Verification session (if available)

        Returns:
            Fare rules information
        """
        payload = {
            "searchId": search_id,
            "flightId": flight_id
        }

        if verify_session:
            payload["verifySession"] = verify_session

        log = logger.bind(
            action="get_fare_rules",
            search_id=search_id,
            flight_id=flight_id
        )
        log.info("Getting fare rules")

        response = await self.post(
            "/api/v1/flights/fare-rules",
            headers=self._get_headers(),
            json_data=payload
        )

        return response

    # ===========================================
    # Booking APIs
    # ===========================================

    async def hold_booking(
        self,
        source: str,
        passengers: list[dict],
        contact: dict,
        search_id: Optional[str] = None,
        flight_id: Optional[str] = None,
        verify_session: Optional[str] = None,
        list_flight_fare: Optional[list] = None
    ) -> BookingResponse:
        """
        Create a booking hold.

        Args:
            source: GDS source (VNA, QH, VJ)
            passengers: List of passenger info
            contact: Contact information
            search_id: Search ID (for direct booking)
            flight_id: Flight ID (for direct booking)
            verify_session: Verification session (for verified booking)
            list_flight_fare: Flight fare list (for verified booking)

        Returns:
            BookingResponse with PNR and status
        """
        payload = {
            "source": source.upper(),
            "listPax": passengers,
            "contact": contact
        }

        # Add either direct booking params or verified booking params
        if verify_session and list_flight_fare:
            payload["verifySession"] = verify_session
            payload["listFlightFare"] = list_flight_fare
        else:
            payload["searchId"] = search_id
            payload["flightId"] = flight_id

        log = logger.bind(
            action="hold_booking",
            source=source,
            num_passengers=len(passengers)
        )
        log.info("Creating booking hold")

        try:
            response = await self.post(
                "/api/v1/flights/booking/hold",
                headers=self._get_headers(),
                json_data=payload
            )

            return BookingResponse(
                success=True,
                booking_code=response.get("pnr") or response.get("bookingCode"),
                status=response.get("status", "HELD"),
                total_price=response.get("totalPrice"),
                time_limit=response.get("timeLimit"),
                raw_response=response
            )
        except APIError as e:
            return BookingResponse(
                success=False,
                status="FAILED",
                message=str(e),
                raw_response=e.response
            )

    async def get_pnr_history(
        self,
        booking_code: str,
        source: str = "VNA",
        last_name: Optional[str] = None
    ) -> PNRHistoryResponse:
        """
        Get PNR/booking history.

        Args:
            booking_code: PNR/booking code
            source: GDS source
            last_name: Passenger last name (optional)

        Returns:
            PNRHistoryResponse with booking details
        """
        payload = {
            "bookingCode": booking_code,
            "source": source.upper()
        }

        if last_name:
            payload["lastName"] = last_name

        log = logger.bind(
            action="get_pnr_history",
            booking_code=booking_code,
            source=source
        )
        log.info("Getting PNR history")

        try:
            response = await self.post(
                "/api/v1/flights/booking/history-pnr",
                headers=self._get_headers(),
                json_data=payload
            )

            return PNRHistoryResponse(
                success=True,
                booking_code=booking_code,
                status=response.get("status", "UNKNOWN"),
                passengers=response.get("passengers"),
                flights=response.get("flights"),
                contact=response.get("contact"),
                price_info=response.get("priceInfo"),
                raw_response=response
            )
        except APIError as e:
            return PNRHistoryResponse(
                success=False,
                booking_code=booking_code,
                status="FAILED",
                raw_response=e.response
            )

    # ===========================================
    # Response Parsing Helpers
    # ===========================================

    def _parse_search_response(
        self,
        response: dict,
        search_params: dict
    ) -> FlightSearchResponse:
        """Parse flight search response into structured model."""
        flights = []

        # SFTech API returns data in "Data" field
        data = response.get("Data") or response.get("data") or response
        raw_flights = data.get("flights") or []

        # Generate search ID if not provided
        search_id = data.get("searchId") or response.get("searchId") or str(uuid.uuid4())

        for idx, flight_data in enumerate(raw_flights):
            try:
                flight = self._parse_flight_option(flight_data, idx)
                if flight:
                    flights.append(flight)
            except Exception as e:
                logger.warning(
                    "Failed to parse flight",
                    error=str(e),
                    flight_data=flight_data
                )

        return FlightSearchResponse(
            search_id=search_id,
            flights=flights,
            total_results=data.get("totalResults") or len(flights),
            has_more=data.get("hasMore", len(flights) >= 20),
            search_params=search_params
        )

    def _parse_flight_option(
        self,
        data: dict,
        index: int
    ) -> Optional[FlightOption]:
        """Parse a single flight option."""
        if not data:
            return None

        # Extract segments
        segments = []
        raw_segments = data.get("segments") or data.get("legs") or [data]

        for seg in raw_segments:
            # Handle both formats: segment-level or flight-level departure/arrival
            departure = seg.get("departure", {})
            arrival = seg.get("arrival", {})

            segment = FlightSegment(
                flight_number=seg.get("flightNumber", ""),
                airline=seg.get("airline") or seg.get("carrier", ""),
                airline_name=seg.get("airlineName"),
                origin=departure.get("code") or seg.get("origin", ""),
                destination=arrival.get("code") or seg.get("destination", ""),
                departure_time=seg.get("scheduledDeparture") or seg.get("departureTime", ""),
                arrival_time=seg.get("scheduledArrival") or seg.get("arrivalTime", ""),
                duration=seg.get("duration"),
                aircraft=seg.get("aircraft"),
                operating_carrier=seg.get("operatingCarrier")
            )
            segments.append(segment)

        # Extract pricing - API returns "price" directly as integer
        price = data.get("price") or data.get("totalPrice") or 0
        if isinstance(price, dict):
            price = price.get("amount", 0)

        return FlightOption(
            id=data.get("id") or data.get("flightId") or f"flight_{index}",
            source=data.get("source") or self.source,
            segments=segments,
            total_price=float(price),
            currency=data.get("currency", "VND"),
            cabin_class=data.get("cabinClass", "ECONOMY"),
            available_seats=data.get("availableSeats"),
            baggage_allowance=data.get("baggageAllowance"),
            refundable=data.get("refundable"),
            fare_basis=data.get("fareBasis"),
            raw_data=data
        )

    def _parse_flight_details(self, response: dict) -> FlightDetails:
        """Parse flight details response."""
        data = response.get("data") or response

        return FlightDetails(
            flight_number=data.get("flightNumber", ""),
            airline=data.get("airline") or data.get("carrier", ""),
            origin=data.get("origin", ""),
            destination=data.get("destination", ""),
            departure_date=data.get("departureDate", ""),
            departure_time=data.get("departureTime", ""),
            arrival_time=data.get("arrivalTime", ""),
            duration=data.get("duration", 0),
            aircraft=data.get("aircraft"),
            status=data.get("status"),
            fare_classes=data.get("fareClasses"),
            amenities=data.get("amenities")
        )
