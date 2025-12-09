"""
Chat component for Streamlit demo.
"""
import streamlit as st

from src.core.capabilities import get_available_capabilities


def render_message(message: dict):
    """Render a single chat message."""
    role = message.get("role", "user")
    content = message.get("content", "")

    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="✈️"):
            st.markdown(content)


def render_chat_history(messages: list):
    """Render full chat history."""
    for message in messages:
        render_message(message)


def render_typing_indicator():
    """Render typing indicator while waiting for response."""
    with st.chat_message("assistant", avatar="✈️"):
        st.markdown("_Đang xử lý..._")


def get_quick_actions() -> list[str]:
    """
    Get list of quick action buttons from available capabilities.
    Only shows examples for capabilities that are actually available.
    """
    available = get_available_capabilities()

    if not available:
        # No capabilities available - show a helpful message action
        return [
            "👋 Xin chào",
            "❓ Bạn có thể giúp gì?",
        ]

    # Build quick actions from available capability examples
    actions = []
    emoji_map = {
        "flight_search": "🔍",
        "booking": "📋",
        "baggage": "🧳",
        "refund": "💰",
        "general": "💬",
    }

    for cap in available:
        if cap.examples:
            # Determine emoji based on capability id
            emoji = "✨"
            for key, em in emoji_map.items():
                if key in cap.id:
                    emoji = em
                    break

            # Add first example as quick action
            actions.append(f"{emoji} {cap.examples[0]}")

    # Limit to 4 quick actions
    return actions[:4] if actions else ["👋 Xin chào", "❓ Bạn có thể giúp gì?"]


def render_quick_actions():
    """Render quick action buttons."""
    st.markdown("**💡 Gợi ý nhanh:**")

    cols = st.columns(2)
    actions = get_quick_actions()

    for i, action in enumerate(actions):
        col_idx = i % 2
        with cols[col_idx]:
            if st.button(action, key=f"quick_{i}", use_container_width=True):
                # Extract text after emoji
                return action.split(" ", 1)[1] if " " in action else action

    return None
