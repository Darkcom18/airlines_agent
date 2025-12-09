"""
Conversation Memory for C1 Travel Agent System.
"""
from typing import Any, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import structlog

logger = structlog.get_logger()


class ConversationMemory:
    """
    Simple in-memory conversation storage.

    For production, this should be replaced with persistent storage
    (PostgreSQL with langgraph checkpointer).
    """

    def __init__(self):
        self._conversations: dict[str, list[BaseMessage]] = {}

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """Get all messages for a session."""
        return self._conversations.get(session_id, [])

    def add_message(self, session_id: str, message: BaseMessage):
        """Add a message to the conversation."""
        if session_id not in self._conversations:
            self._conversations[session_id] = []
        self._conversations[session_id].append(message)

        logger.debug(
            "Message added to memory",
            session_id=session_id,
            message_type=type(message).__name__
        )

    def add_human_message(self, session_id: str, content: str):
        """Add a human message."""
        self.add_message(session_id, HumanMessage(content=content))

    def add_ai_message(self, session_id: str, content: str):
        """Add an AI message."""
        self.add_message(session_id, AIMessage(content=content))

    def clear(self, session_id: str):
        """Clear conversation history for a session."""
        if session_id in self._conversations:
            del self._conversations[session_id]
            logger.info("Conversation cleared", session_id=session_id)

    def get_context_window(
        self,
        session_id: str,
        max_messages: int = 10
    ) -> list[BaseMessage]:
        """Get recent messages as context."""
        messages = self.get_messages(session_id)
        return messages[-max_messages:]


# Global memory instance (for simple use case)
# In production, use dependency injection
memory = ConversationMemory()
