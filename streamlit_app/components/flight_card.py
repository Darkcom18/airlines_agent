"""
Flight card component for displaying flight results.
"""
import streamlit as st


def format_price(price: float, currency: str = "VND") -> str:
    """Format price with thousand separators."""
    return f"{price:,.0f}".replace(",", ".") + f" {currency}"


def render_flight_card(flight: dict, index: int):
    """
    Render a single flight card.

    Args:
        flight: Flight data dictionary
        index: Flight index for display
    """
    segments = flight.get("segments", [])
    if not segments:
        return

    first_seg = segments[0]
    last_seg = segments[-1] if len(segments) > 1 else first_seg

    price = flight.get("total_price", 0)
    currency = flight.get("currency", "VND")

    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            airline = first_seg.get("airline", "")
            flight_num = first_seg.get("flight_number", "")
            st.markdown(f"**{airline} {flight_num}**")

            if len(segments) > 1:
                st.caption(f"🔄 {len(segments) - 1} điểm dừng")
            else:
                st.caption("✈️ Bay thẳng")

        with col2:
            dep_time = first_seg.get("departure_time", "")
            arr_time = last_seg.get("arrival_time", "")
            origin = first_seg.get("origin", "")
            dest = last_seg.get("destination", "")

            st.markdown(f"🕐 **{dep_time}** → **{arr_time}**")
            st.caption(f"{origin} → {dest}")

        with col3:
            st.markdown(f"💰 **{format_price(price, currency)}**")

            if st.button("Chọn", key=f"select_{index}", type="primary"):
                st.session_state.selected_flight = flight
                st.success("Đã chọn chuyến bay!")

        st.divider()


def render_flight_list(flights: list):
    """
    Render list of flights.

    Args:
        flights: List of flight data dictionaries
    """
    if not flights:
        st.info("Không có kết quả tìm kiếm.")
        return

    st.markdown(f"### 🔍 Tìm thấy {len(flights)} chuyến bay")

    for i, flight in enumerate(flights):
        render_flight_card(flight, i)


def render_flight_details(flight: dict):
    """
    Render detailed flight information.

    Args:
        flight: Flight data dictionary
    """
    if not flight:
        return

    st.markdown("### ✈️ Chi tiết chuyến bay")

    segments = flight.get("segments", [])

    for i, seg in enumerate(segments):
        with st.expander(f"Chặng {i + 1}: {seg.get('origin')} → {seg.get('destination')}", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Hãng:** {seg.get('airline', 'N/A')}")
                st.markdown(f"**Số hiệu:** {seg.get('flight_number', 'N/A')}")
                st.markdown(f"**Khởi hành:** {seg.get('departure_time', 'N/A')}")

            with col2:
                st.markdown(f"**Điểm đi:** {seg.get('origin', 'N/A')}")
                st.markdown(f"**Điểm đến:** {seg.get('destination', 'N/A')}")
                st.markdown(f"**Đến nơi:** {seg.get('arrival_time', 'N/A')}")

    # Price summary
    st.markdown("---")
    price = flight.get("total_price", 0)
    currency = flight.get("currency", "VND")
    st.markdown(f"### 💰 Tổng giá: **{format_price(price, currency)}**")
