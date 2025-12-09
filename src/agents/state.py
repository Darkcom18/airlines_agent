"""
LangGraph State Definitions for C1 Travel Agent System.
"""
from typing import Annotated, Any, Literal, Optional, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class FlightSearchParams(BaseModel):
    """Parameters for flight search."""
    search_type: Literal["oneway", "roundtrip", "multicity"] = "oneway"
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    cabin_class: str = "ECONOMY"
    legs: Optional[list[dict]] = None  # For multi-city
    country_suggestions: Optional[list[dict]] = None  # Suggested airports for countries


class FlightSearchResult(BaseModel):
    """Flight search results."""
    search_id: Optional[str] = None
    flights: list[dict] = Field(default_factory=list)
    total_results: int = 0
    has_more: bool = False


class BookingInfo(BaseModel):
    """Booking information."""
    booking_code: Optional[str] = None
    status: Optional[str] = None
    passengers: list[dict] = Field(default_factory=list)
    contact: Optional[dict] = None
    selected_flight: Optional[dict] = None


class AgentState(BaseModel):
    """
    Main state for the travel agent graph.

    This state is passed between agents and accumulates information
    throughout the conversation.
    """
    # Conversation messages (using add_messages reducer)
    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(default_factory=list)

    # Current agent handling the request
    current_agent: Literal[
        "supervisor", "chat", "flight", "booking",
        "ticketing", "pnr", "ancillary"
    ] = "supervisor"

    # Next agent to route to (set by supervisor)
    next_agent: Optional[Literal[
        "chat", "flight", "booking", "ticketing", "pnr", "ancillary", "end"
    ]] = None

    # User intent classification
    intent: Optional[str] = None

    # Flight search context
    flight_search: FlightSearchParams = Field(default_factory=FlightSearchParams)
    flight_results: FlightSearchResult = Field(default_factory=FlightSearchResult)

    # Booking context
    booking: BookingInfo = Field(default_factory=BookingInfo)

    # User context (for authenticated users)
    user_id: Optional[str] = None
    user_email: Optional[str] = None

    # Conversation context
    session_id: Optional[str] = None
    user_language: str = "vi"  # Default Vietnamese

    # Error handling
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class SupervisorDecision(BaseModel):
    """Supervisor's routing decision."""
    next_agent: Literal["chat", "flight", "booking", "ticketing", "pnr", "ancillary", "end"]
    reasoning: str
    extracted_info: Optional[dict] = None
