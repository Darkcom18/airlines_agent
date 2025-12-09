"""
Streamlit Demo App for C1 Travel Agent System.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import os

import streamlit as st

from streamlit_app.components.chat import (
    render_chat_history,
    render_quick_actions
)
from streamlit_app.components.flight_card import render_flight_list

# Import agent only when needed to avoid import issues
def get_process_message():
    from src.agents.graph import process_message
    return process_message


# Page config
st.set_page_config(
    page_title="C1 Travel Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
    }
    .stButton button {
        border-radius: 20px;
    }
    div[data-testid="stSidebarContent"] {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent_state" not in st.session_state:
        st.session_state.agent_state = None

    if "flight_results" not in st.session_state:
        st.session_state.flight_results = None

    if "selected_flight" not in st.session_state:
        st.session_state.selected_flight = None

    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())


async def process_user_message(message: str):
    """Process user message through the agent system."""
    process_message = get_process_message()

    result = await process_message(
        message=message,
        session_id=st.session_state.session_id,
        existing_state=st.session_state.agent_state
    )

    return result


def main():
    """Main application."""
    init_session_state()

    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/airplane-take-off.png", width=80)
        st.title("C1 Travel Agent")
        st.markdown("---")

        st.markdown("### 📊 Trạng thái")
        st.markdown(f"**Session:** `{st.session_state.session_id[:8]}...`")

        if st.session_state.agent_state:
            agent = getattr(st.session_state.agent_state, 'current_agent', 'N/A')
            st.markdown(f"**Agent:** {agent}")

        st.markdown("---")

        # Flight results in sidebar if available
        if st.session_state.flight_results:
            flights = st.session_state.flight_results.get("flights", [])
            total = st.session_state.flight_results.get("total_results", 0)

            st.markdown(f"### 🔍 Kết quả ({total} chuyến)")

            for i, flight in enumerate(flights[:5]):
                segs = flight.get("segments", [])
                if segs:
                    first = segs[0]
                    price = flight.get("total_price", 0)
                    st.markdown(
                        f"**{first.get('airline', '')} {first.get('flight_number', '')}**\n"
                        f"{first.get('departure_time', '')} | "
                        f"{price:,.0f}".replace(",", ".") + " VND"
                    )
                    st.markdown("---")

        # Clear chat button
        if st.button("🗑️ Xóa cuộc trò chuyện", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent_state = None
            st.session_state.flight_results = None
            st.session_state.selected_flight = None
            st.rerun()

    # Main content
    st.title("✈️ Travel Assistant")
    st.markdown("Xin chào! Tôi có thể giúp bạn tìm kiếm và đặt vé máy bay.")

    # Quick actions for new conversations
    if not st.session_state.messages:
        quick_message = render_quick_actions()
        if quick_message:
            st.session_state.messages.append({
                "role": "user",
                "content": quick_message
            })
            st.rerun()

    # Chat history
    render_chat_history(st.session_state.messages)

    # Chat input
    if prompt := st.chat_input("Nhập tin nhắn của bạn..."):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Process and display response
        with st.chat_message("assistant", avatar="✈️"):
            with st.spinner("Đang xử lý..."):
                try:
                    # Run async function
                    result = asyncio.run(process_user_message(prompt))

                    response = result.get("response", "")
                    st.markdown(response)

                    # Update state
                    st.session_state.agent_state = result.get("state")

                    # Update flight results if available
                    flight_results = result.get("flight_results")
                    if flight_results and hasattr(flight_results, 'flights'):
                        st.session_state.flight_results = {
                            "search_id": flight_results.search_id,
                            "flights": flight_results.flights,
                            "total_results": flight_results.total_results
                        }

                    # Add assistant message to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })

                except Exception as e:
                    error_msg = f"Lỗi: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })


if __name__ == "__main__":
    main()
