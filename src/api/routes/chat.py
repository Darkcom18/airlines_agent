"""
Chat API endpoints for C1 Travel Agent System.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
import structlog

from src.api.schemas import ChatRequest, ChatResponse, ErrorResponse
from src.agents.graph import process_message
from src.agents.state import AgentState

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chat"])

# In-memory session storage (replace with Redis/DB in production)
_sessions: dict[str, AgentState] = {}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message through the travel agent system.

    This endpoint:
    1. Routes the message to the appropriate agent (supervisor decides)
    2. Processes the request (chat, flight search, booking)
    3. Returns the AI response

    Args:
        request: ChatRequest with message and optional session_id

    Returns:
        ChatResponse with AI response and session info
    """
    # Get or create session ID
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        "Chat request received",
        session_id=session_id,
        message_preview=request.message[:50]
    )

    # Get existing state if session exists
    existing_state = _sessions.get(session_id)

    try:
        # Process message through agent graph
        result = await process_message(
            message=request.message,
            session_id=session_id,
            existing_state=existing_state
        )

        # Store updated state
        if result.get("state"):
            _sessions[session_id] = result["state"]

        # Build response
        response = ChatResponse(
            response=result.get("response", ""),
            session_id=session_id,
            agent=result.get("agent", "unknown"),
            intent=result.get("intent")
        )

        # Include flight results if available
        flight_results = result.get("flight_results")
        if flight_results:
            response.flight_results = {
                "search_id": flight_results.search_id,
                "total_results": flight_results.total_results,
                "flights": flight_results.flights[:5]  # Top 5 for API response
            }

        logger.info(
            "Chat response generated",
            session_id=session_id,
            agent=response.agent
        )

        return response

    except Exception as e:
        logger.error("Chat processing error", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """
    Clear a chat session.

    Args:
        session_id: Session ID to clear

    Returns:
        Confirmation message
    """
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info("Session cleared", session_id=session_id)
        return {"message": f"Session {session_id} cleared"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/{session_id}/history")
async def get_history(session_id: str):
    """
    Get chat history for a session.

    Args:
        session_id: Session ID

    Returns:
        List of messages in the session
    """
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = []
    for msg in state.messages:
        messages.append({
            "type": type(msg).__name__,
            "content": msg.content
        })

    return {"session_id": session_id, "messages": messages}
