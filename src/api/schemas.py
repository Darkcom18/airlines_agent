"""
API Request/Response Schemas for C1 Travel Agent System.
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    agent: str = Field(..., description="Agent that handled the request")
    intent: Optional[str] = Field(None, description="Detected user intent")

    # Optional flight results
    flight_results: Optional[dict] = Field(None, description="Flight search results if applicable")


class FlightSearchRequest(BaseModel):
    """Request model for direct flight search endpoint."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(None, description="Return date for roundtrip")
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=9)
    infants: int = Field(default=0, ge=0, le=9)
    cabin_class: str = Field(default="ECONOMY")


class FlightSearchResponse(BaseModel):
    """Response model for flight search endpoint."""
    search_id: str
    flights: list[dict]
    total_results: int
    has_more: bool = False


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = "healthy"
    version: str = "1.0.0"
    services: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
