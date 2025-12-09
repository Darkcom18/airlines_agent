"""
Pydantic models for SFTech API requests and responses.
"""
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CabinClass(str, Enum):
    """Cabin class options."""
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"


class GDSSource(str, Enum):
    """GDS source options."""
    VNA = "VNA"
    QH = "QH"  # Bamboo Airways
    VJ = "VJ"  # VietJet
    SABRE = "SABRE"


class PassengerType(str, Enum):
    """Passenger type options."""
    ADULT = "ADT"
    CHILD = "CHD"
    INFANT = "INF"


# ===========================================
# Flight Search Models
# ===========================================

class FlightLeg(BaseModel):
    """Flight leg for multi-city search."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")


class FlightSearchRequest(BaseModel):
    """Request model for flight search."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(None, description="Return date for roundtrip (YYYY-MM-DD)")
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=9)
    infants: int = Field(default=0, ge=0, le=9)
    cabin_class: CabinClass = Field(default=CabinClass.ECONOMY)

    # Multi-city specific
    legs: Optional[list[FlightLeg]] = Field(None, description="Flight legs for multi-city search")


class FlightSegment(BaseModel):
    """A single flight segment."""
    flight_number: str
    airline: str
    airline_name: Optional[str] = None
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration: Optional[int] = None  # Duration in minutes
    aircraft: Optional[str] = None
    operating_carrier: Optional[str] = None


class FlightOption(BaseModel):
    """A flight option with pricing."""
    id: str
    source: str  # GDS source
    segments: list[FlightSegment]
    total_price: float
    currency: str = "VND"
    cabin_class: str
    available_seats: Optional[int] = None
    baggage_allowance: Optional[str] = None
    refundable: Optional[bool] = None
    fare_basis: Optional[str] = None

    # Additional fields from API
    raw_data: Optional[dict] = None


class FlightSearchResponse(BaseModel):
    """Response model for flight search."""
    search_id: str
    flights: list[FlightOption]
    total_results: int
    has_more: bool = False
    search_params: dict


# ===========================================
# Flight Details Models
# ===========================================

class FlightDetails(BaseModel):
    """Detailed flight information."""
    flight_number: str
    airline: str
    origin: str
    destination: str
    departure_date: str
    departure_time: str
    arrival_time: str
    duration: int
    aircraft: Optional[str] = None
    status: Optional[str] = None
    fare_classes: Optional[list[dict]] = None
    amenities: Optional[list[str]] = None


# ===========================================
# Booking Models
# ===========================================

class PassengerInfo(BaseModel):
    """Passenger information for booking."""
    type: PassengerType = PassengerType.ADULT
    title: str = Field(..., description="Mr, Mrs, Ms, etc.")
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None  # YYYY-MM-DD
    passport_number: Optional[str] = None
    passport_expiry: Optional[str] = None
    nationality: Optional[str] = None


class ContactInfo(BaseModel):
    """Contact information for booking."""
    email: str
    phone: str
    address: Optional[str] = None


class BookingRequest(BaseModel):
    """Request model for booking hold."""
    source: str = Field(..., description="GDS source (VNA, QH, VJ)")
    search_id: str
    flight_id: str
    passengers: list[PassengerInfo]
    contact: ContactInfo

    # For verified booking
    verify_session: Optional[str] = None
    list_flight_fare: Optional[list[dict]] = None


class BookingResponse(BaseModel):
    """Response model for booking."""
    success: bool
    booking_code: Optional[str] = None  # PNR
    status: str
    message: Optional[str] = None
    total_price: Optional[float] = None
    currency: str = "VND"
    time_limit: Optional[str] = None  # Booking hold time limit
    raw_response: Optional[dict] = None


# ===========================================
# PNR History Models
# ===========================================

class PNRHistoryRequest(BaseModel):
    """Request model for PNR history lookup."""
    booking_code: str
    source: str = "VNA"
    last_name: Optional[str] = None


class PNRHistoryResponse(BaseModel):
    """Response model for PNR history."""
    success: bool
    booking_code: str
    status: str
    passengers: Optional[list[dict]] = None
    flights: Optional[list[dict]] = None
    contact: Optional[dict] = None
    price_info: Optional[dict] = None
    raw_response: Optional[dict] = None
