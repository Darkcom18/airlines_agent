"""
Chat Agent for C1 Travel Agent System.
Handles general consultation and FAQ.
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import structlog

from src.core.llm import get_llm
from src.core.capabilities import (
    is_capability_available,
    get_not_supported_message,
)
from .state import AgentState
from .prompts import CHAT_AGENT_PROMPT

logger = structlog.get_logger()

# Keywords to detect specific policy questions
BAGGAGE_KEYWORDS = ["hành lý", "hanh ly", "baggage", "luggage", "ký gửi", "ky gui", "xách tay", "xach tay", "kg", "cân"]
REFUND_KEYWORDS = ["hoàn vé", "hoan ve", "đổi vé", "doi ve", "refund", "hủy vé", "huy ve", "đổi ngày", "doi ngay"]


def detect_policy_capability(message: str) -> str | None:
    """
    Detect if message is asking about a specific policy.
    Returns capability_id if detected, None otherwise.
    """
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in BAGGAGE_KEYWORDS):
        return "baggage_policy"
    if any(kw in msg_lower for kw in REFUND_KEYWORDS):
        return "refund_policy"

    return None


async def chat_agent_node(state: AgentState) -> dict:
    """
    Chat agent for general travel consultation.

    Args:
        state: Current agent state

    Returns:
        Updated state with AI response message
    """
    logger.info("Chat agent processing request")

    # Get last user message
    last_message = ""
    if state.messages:
        last_message = state.messages[-1].content

    # Check if asking about specific policy
    policy_capability = detect_policy_capability(last_message)
    if policy_capability and not is_capability_available(policy_capability):
        logger.info(f"Capability {policy_capability} not available")
        return {
            "messages": [AIMessage(content=get_not_supported_message(policy_capability))],
            "current_agent": "chat"
        }

    llm = get_llm(temperature=0.7)

    # Build messages for LLM
    messages = [SystemMessage(content=CHAT_AGENT_PROMPT)]

    # Add conversation history (last 10 messages for context)
    for msg in state.messages[-10:]:
        messages.append(msg)

    try:
        response = await llm.ainvoke(messages)

        logger.info(
            "Chat agent response generated",
            response_length=len(response.content)
        )

        return {
            "messages": [AIMessage(content=response.content)],
            "current_agent": "chat"
        }

    except Exception as e:
        logger.error("Chat agent error", error=str(e))
        return {
            "messages": [AIMessage(
                content="Xin lỗi, tôi gặp sự cố khi xử lý yêu cầu. Vui lòng thử lại."
            )],
            "error": str(e)
        }
