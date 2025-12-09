"""
Main LangGraph for C1 Travel Agent System.
Orchestrates the multi-agent workflow.
"""
from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
import structlog

from .state import AgentState
from .supervisor import supervisor_node, should_continue
from .chat_agent import chat_agent_node
from .flight_agent import flight_agent_node
from .booking_agent import booking_agent_node
from .ticketing_agent import ticketing_agent_node
from .pnr_agent import pnr_agent_node
from .ancillary_agent import ancillary_agent_node

logger = structlog.get_logger()


def create_agent_graph() -> StateGraph:
    """
    Create the main agent graph with supervisor pattern.

    Graph structure:
        START → supervisor → [chat | flight | booking | ticketing | pnr | ancillary] → END
                    ↑_______________________________________________________________|

    Agents:
        - chat_agent: General Q&A and travel consultation
        - flight_agent: Flight search across multiple sources
        - booking_agent: Create bookings and hold flights
        - ticketing_agent: Issue, void, reissue tickets
        - pnr_agent: PNR management and modifications
        - ancillary_agent: Seats, baggage, meals

    Returns:
        Compiled StateGraph
    """
    logger.info("Creating agent graph with 6 specialized agents")

    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("chat_agent", chat_agent_node)
    graph.add_node("flight_agent", flight_agent_node)
    graph.add_node("booking_agent", booking_agent_node)
    graph.add_node("ticketing_agent", ticketing_agent_node)
    graph.add_node("pnr_agent", pnr_agent_node)
    graph.add_node("ancillary_agent", ancillary_agent_node)

    # Set entry point
    graph.set_entry_point("supervisor")

    # Add conditional edges from supervisor
    graph.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "chat_agent": "chat_agent",
            "flight_agent": "flight_agent",
            "booking_agent": "booking_agent",
            "ticketing_agent": "ticketing_agent",
            "pnr_agent": "pnr_agent",
            "ancillary_agent": "ancillary_agent",
            "end": END
        }
    )

    # All agents return to END after processing
    graph.add_edge("chat_agent", END)
    graph.add_edge("flight_agent", END)
    graph.add_edge("booking_agent", END)
    graph.add_edge("ticketing_agent", END)
    graph.add_edge("pnr_agent", END)
    graph.add_edge("ancillary_agent", END)

    # Compile the graph
    compiled = graph.compile()

    logger.info("Agent graph created successfully with 6 agents")

    return compiled


# Create default graph instance
agent_graph = create_agent_graph()


async def process_message(
    message: str,
    session_id: str = "default",
    existing_state: AgentState = None,
    user_id: str = None
) -> dict:
    """
    Process a user message through the agent graph.

    Args:
        message: User's input message
        session_id: Session identifier for conversation tracking
        existing_state: Existing state to continue from
        user_id: Optional user ID for authenticated users

    Returns:
        Response dict with:
        - response: AI response text
        - state: Updated agent state
        - agent: Which agent handled the request
    """
    from langchain_core.messages import HumanMessage

    logger.info(
        "Processing message",
        session_id=session_id,
        user_id=user_id,
        message_preview=message[:50] if len(message) > 50 else message
    )

    # Build initial state
    if existing_state:
        # Add new message to existing state
        initial_state = existing_state.model_copy()
        initial_state.messages = list(existing_state.messages) + [HumanMessage(content=message)]
        if user_id:
            initial_state.user_id = user_id
    else:
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            user_id=user_id
        )

    # Run the graph
    try:
        result = await agent_graph.ainvoke(initial_state)

        # Extract response from last AI message
        response_text = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                response_text = msg.content
                break

        return {
            "response": response_text,
            "state": AgentState(**result),
            "agent": result.get("current_agent", "unknown"),
            "intent": result.get("intent"),
            "flight_results": result.get("flight_results")
        }

    except Exception as e:
        logger.error("Graph execution error", error=str(e))
        return {
            "response": "Xin lỗi, đã xảy ra lỗi. Vui lòng thử lại sau.",
            "state": initial_state,
            "agent": "error",
            "error": str(e)
        }
