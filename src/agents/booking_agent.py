"""
Booking Agent for C1 Travel Agent System.
Handles booking creation and PNR management.
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import structlog

from src.core.llm import get_llm
from src.core.capabilities import is_capability_available, get_not_supported_message
from src.mcp_server.api_client.sftech import SFTechClient
from .state import AgentState
from .prompts import BOOKING_AGENT_PROMPT

logger = structlog.get_logger()


async def get_pnr_history(booking_code: str, source: str = "VNA") -> dict:
    """Retrieve PNR history from API."""
    client = SFTechClient(source="F1")

    try:
        result = await client.get_pnr_history(
            booking_code=booking_code,
            source=source
        )

        return {
            "success": result.success,
            "booking_code": result.booking_code,
            "status": result.status,
            "passengers": result.passengers,
            "flights": result.flights,
            "contact": result.contact,
            "price_info": result.price_info
        }

    except Exception as e:
        logger.error("PNR lookup error", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        await client.close()


def format_booking_info(result: dict) -> str:
    """Format booking information for display."""
    if not result.get("success"):
        return f"❌ Không thể tra cứu booking: {result.get('error', 'Lỗi không xác định')}"

    lines = [
        "📋 **THÔNG TIN BOOKING**",
        "",
        f"🔖 Mã booking: **{result.get('booking_code', 'N/A')}**",
        f"📊 Trạng thái: {result.get('status', 'UNKNOWN')}",
        ""
    ]

    # Flights
    flights = result.get("flights", [])
    if flights:
        lines.append("✈️ **Chuyến bay:**")
        for flight in flights:
            lines.append(f"   {flight.get('airline', '')} {flight.get('flight_number', '')}")
            lines.append(f"   {flight.get('origin', '')} → {flight.get('destination', '')}")
            lines.append(f"   {flight.get('departure_date', '')} | {flight.get('departure_time', '')}")
        lines.append("")

    # Passengers
    passengers = result.get("passengers", [])
    if passengers:
        lines.append("👥 **Hành khách:**")
        for i, pax in enumerate(passengers, 1):
            name = f"{pax.get('first_name', '')} {pax.get('last_name', '')}"
            pax_type = pax.get("type", "ADT")
            lines.append(f"   {i}. {name} ({pax_type})")
        lines.append("")

    # Price info
    price_info = result.get("price_info", {})
    if price_info:
        total = price_info.get("total", 0)
        currency = price_info.get("currency", "VND")
        price_formatted = f"{total:,.0f}".replace(",", ".")
        lines.append(f"💰 **Tổng tiền:** {price_formatted} {currency}")

    return "\n".join(lines)


async def booking_agent_node(state: AgentState) -> dict:
    """
    Booking agent for creating bookings and managing PNRs.

    Args:
        state: Current agent state

    Returns:
        Updated state with booking info and response message
    """
    logger.info("Booking agent processing request")

    # Get last message to understand request
    messages = state.messages
    if not messages:
        return {
            "messages": [AIMessage(
                content="Bạn muốn đặt vé hay tra cứu booking? Vui lòng cho tôi biết thêm chi tiết."
            )],
            "current_agent": "booking"
        }

    last_message = messages[-1].content.lower()

    # Check if user wants to lookup PNR
    pnr_keywords = ["pnr", "booking", "mã đặt", "tra cứu", "kiểm tra"]
    is_pnr_lookup = any(kw in last_message for kw in pnr_keywords)

    if is_pnr_lookup:
        # Check capability for booking lookup
        if not is_capability_available("booking_lookup"):
            logger.info("Capability booking_lookup not available")
            return {
                "messages": [AIMessage(content=get_not_supported_message("booking_lookup"))],
                "current_agent": "booking"
            }
        # Try to extract PNR code (usually 6 uppercase letters)
        import re
        pnr_match = re.search(r'\b[A-Z0-9]{6}\b', messages[-1].content)

        if pnr_match:
            pnr_code = pnr_match.group()
            logger.info("Looking up PNR", pnr=pnr_code)

            result = await get_pnr_history(pnr_code)
            response = format_booking_info(result)

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "booking"
            }
        else:
            return {
                "messages": [AIMessage(
                    content="Vui lòng cung cấp mã booking (PNR) 6 ký tự để tra cứu.\n\nVí dụ: 'Tra cứu booking ABC123'"
                )],
                "current_agent": "booking"
            }

    # Check if user wants to create booking
    if state.flight_results and state.flight_results.flights:
        # Check capability for booking create
        if not is_capability_available("booking_create"):
            logger.info("Capability booking_create not available")
            return {
                "messages": [AIMessage(content=get_not_supported_message("booking_create"))],
                "current_agent": "booking"
            }

        # User has flight results, can proceed to booking
        llm = get_llm(temperature=0.7)

        context_messages = [
            SystemMessage(content=BOOKING_AGENT_PROMPT),
            HumanMessage(content=f"""
Người dùng đã tìm được chuyến bay và muốn đặt vé.
Kết quả tìm kiếm: {len(state.flight_results.flights)} chuyến bay

Tin nhắn người dùng: {messages[-1].content}

Hãy hướng dẫn họ chọn chuyến bay và cung cấp thông tin để đặt vé.
""")
        ]

        response = await llm.ainvoke(context_messages)

        return {
            "messages": [AIMessage(content=response.content)],
            "current_agent": "booking"
        }

    else:
        # No flight results, guide user to search first
        return {
            "messages": [AIMessage(
                content="Để đặt vé, bạn cần tìm chuyến bay trước. Hãy cho tôi biết:\n"
                        "- Điểm đi (VD: SGN, HAN)\n"
                        "- Điểm đến\n"
                        "- Ngày bay\n"
                        "- Số lượng hành khách"
            )],
            "current_agent": "booking"
        }
