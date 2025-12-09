"""
Ancillary Agent for C1 Travel Agent System.
Handles seats, baggage, meals, and other ancillary services.
"""
import re
from langchain_core.messages import AIMessage
import structlog

from src.mcp_server.tools import get_registry
from src.core.capabilities import is_capability_available, get_not_supported_message
from .state import AgentState

logger = structlog.get_logger()


def format_seat_map(result: dict) -> str:
    """Format seat map for display."""
    if not result.get("success"):
        return f"❌ Không thể lấy sơ đồ ghế: {result.get('error', 'Lỗi')}"

    lines = [
        "💺 **SƠ ĐỒ GHẾ**",
        "",
        f"✈️ Loại máy bay: {result.get('aircraft_type', 'N/A')}",
        f"🎫 Hạng: {result.get('cabin_class', 'ECONOMY')}",
        ""
    ]

    available = result.get("available_seats", [])
    if available:
        lines.append(f"**Ghế trống:** {len(available)} ghế")
        # Group by row
        rows = {}
        for seat in available[:30]:  # Limit display
            row = seat[:-1]
            if row not in rows:
                rows[row] = []
            rows[row].append(seat[-1])

        for row, cols in sorted(rows.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            lines.append(f"   Hàng {row}: {', '.join(sorted(cols))}")

    prices = result.get("seat_prices", {})
    if prices:
        lines.append("")
        lines.append("**Giá ghế:**")
        for category, price in prices.items():
            lines.append(f"   • {category}: {price:,.0f} VND".replace(",", "."))

    return "\n".join(lines)


def format_baggage_options(result: dict) -> str:
    """Format baggage options for display."""
    lines = [
        "🧳 **TÙY CHỌN HÀNH LÝ**",
        "",
        f"📦 Hành lý bao gồm: {result.get('included_allowance', 'Xem chi tiết vé')}",
        ""
    ]

    options = result.get("options", [])
    if options:
        lines.append("**Mua thêm hành lý:**")
        for opt in options:
            code = opt.get("code", "")
            weight = opt.get("weight", "")
            price = opt.get("price", 0)
            lines.append(f"   • {code}: {weight}kg - {price:,.0f} VND".replace(",", "."))

    return "\n".join(lines)


async def ancillary_agent_node(state: AgentState) -> dict:
    """
    Ancillary agent for managing additional services.
    """
    logger.info("Ancillary agent processing request")

    messages = state.messages
    if not messages:
        return {
            "messages": [AIMessage(
                content="Bạn cần dịch vụ bổ sung gì? Tôi có thể hỗ trợ:\n"
                        "• 💺 Chọn ghế ngồi\n"
                        "• 🧳 Mua thêm hành lý\n"
                        "• 🍽️ Đặt suất ăn đặc biệt\n"
            )],
            "current_agent": "ancillary"
        }

    last_message = messages[-1].content.lower()
    registry = get_registry()

    # Check capability
    if not is_capability_available("ancillary"):
        return {
            "messages": [AIMessage(content=get_not_supported_message("ancillary"))],
            "current_agent": "ancillary"
        }

    # Extract PNR code if present
    pnr_match = re.search(r'\b[A-Z0-9]{6}\b', messages[-1].content)
    pnr_code = pnr_match.group() if pnr_match else None

    # Detect intent - Seat selection
    if any(kw in last_message for kw in ["ghế", "seat", "chỗ ngồi"]):
        if "xem" in last_message or "sơ đồ" in last_message or "map" in last_message:
            # Get seat map
            if pnr_code:
                result = await registry.call("get_seat_map", {
                    "booking_code": pnr_code,
                    "segment_index": 0
                })
                response = format_seat_map(result)
            else:
                response = (
                    "Vui lòng cung cấp mã booking (PNR) để xem sơ đồ ghế.\n\n"
                    "Ví dụ: 'Xem sơ đồ ghế PNR ABC123'"
                )

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ancillary"
            }

        elif "chọn" in last_message or "đặt" in last_message or "select" in last_message:
            # Select seat
            seat_match = re.search(r'\b(\d{1,2}[A-K])\b', messages[-1].content.upper())

            if pnr_code and seat_match:
                seat_number = seat_match.group(1)

                result = await registry.call("select_seat", {
                    "booking_code": pnr_code,
                    "passenger_index": 0,
                    "segment_index": 0,
                    "seat_number": seat_number
                })

                if result.get("success"):
                    price = result.get("price", 0)
                    response = (
                        f"✅ **Đã chọn ghế thành công!**\n\n"
                        f"💺 Ghế: **{seat_number}**\n"
                        f"💰 Phí: {price:,.0f} VND\n\n"
                        f"Ghế đã được gán cho hành khách 1."
                    )
                else:
                    response = f"❌ Không thể chọn ghế {seat_number}: {result.get('message', 'Ghế không khả dụng')}"
            else:
                response = (
                    "Để chọn ghế, tôi cần:\n"
                    "• Mã booking (PNR)\n"
                    "• Số ghế (VD: 12A, 15C)\n\n"
                    "Ví dụ: 'Chọn ghế 12A cho PNR ABC123'"
                )

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ancillary"
            }

    # Detect intent - Baggage
    elif any(kw in last_message for kw in ["hành lý", "baggage", "vali", "túi"]):
        if "xem" in last_message or "giá" in last_message or "option" in last_message:
            # Get baggage options
            if pnr_code:
                result = await registry.call("get_baggage_options", {
                    "booking_code": pnr_code
                })
                response = format_baggage_options(result)
            else:
                response = (
                    "Vui lòng cung cấp mã booking để xem tùy chọn hành lý.\n\n"
                    "Ví dụ: 'Xem hành lý PNR ABC123'"
                )

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ancillary"
            }

        elif "mua" in last_message or "thêm" in last_message or "add" in last_message:
            # Add baggage
            weight_match = re.search(r'(\d{2})\s*kg', last_message)

            if pnr_code:
                weight_kg = int(weight_match.group(1)) if weight_match else 20
                baggage_code = f"BAG{weight_kg}"

                result = await registry.call("add_baggage", {
                    "booking_code": pnr_code,
                    "passenger_index": 0,
                    "baggage_code": baggage_code,
                    "weight_kg": weight_kg
                })

                if result.get("success"):
                    price = result.get("price", 0)
                    response = (
                        f"✅ **Đã thêm hành lý!**\n\n"
                        f"🧳 Loại: {weight_kg}kg\n"
                        f"💰 Phí: {price:,.0f} VND"
                    )
                else:
                    response = f"❌ Không thể thêm hành lý: {result.get('message', 'Lỗi')}"
            else:
                response = (
                    "Để mua thêm hành lý, tôi cần mã booking.\n\n"
                    "Ví dụ: 'Mua 20kg hành lý cho PNR ABC123'"
                )

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ancillary"
            }

    # Detect intent - Meals
    elif any(kw in last_message for kw in ["ăn", "meal", "suất ăn", "đồ ăn"]):
        if "xem" in last_message or "option" in last_message:
            # Get meal options
            if pnr_code:
                result = await registry.call("get_meal_options", {
                    "booking_code": pnr_code
                })

                options = result.get("options", [])
                lines = ["🍽️ **SUẤT ĂN ĐẶC BIỆT**", ""]
                for opt in options:
                    lines.append(f"• **{opt['code']}** - {opt['name']}")
                    lines.append(f"  {opt.get('description', '')}")

                lines.append("")
                lines.append("Để đặt, nhắn: 'Đặt suất ăn VGML cho PNR ABC123'")
                response = "\n".join(lines)
            else:
                response = "Vui lòng cung cấp mã booking để xem suất ăn."

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ancillary"
            }

        elif "đặt" in last_message or "chọn" in last_message:
            # Add special meal
            meal_codes = ["VGML", "AVML", "HNML", "MOML", "DBML", "GFML", "KSML", "CHML"]
            meal_match = None
            for code in meal_codes:
                if code.lower() in last_message or code in messages[-1].content.upper():
                    meal_match = code
                    break

            if pnr_code and meal_match:
                result = await registry.call("add_special_meal", {
                    "booking_code": pnr_code,
                    "passenger_index": 0,
                    "meal_code": meal_match
                })

                if result.get("success"):
                    response = (
                        f"✅ **Đã đặt suất ăn đặc biệt!**\n\n"
                        f"🍽️ Loại: {meal_match}\n"
                        f"📋 PNR: {pnr_code}"
                    )
                else:
                    response = f"❌ Không thể đặt suất ăn: {result.get('message')}"
            else:
                response = (
                    "Để đặt suất ăn, tôi cần:\n"
                    "• Mã booking (PNR)\n"
                    "• Loại suất ăn (VD: VGML, AVML)\n\n"
                    "Gõ 'xem suất ăn' để xem các loại có sẵn."
                )

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ancillary"
            }

    # Default help
    return {
        "messages": [AIMessage(
            content="✨ **DỊCH VỤ BỔ SUNG**\n\n"
                    "Tôi có thể hỗ trợ:\n\n"
                    "**💺 Ghế ngồi:**\n"
                    "• 'Xem sơ đồ ghế PNR ABC123'\n"
                    "• 'Chọn ghế 12A cho PNR ABC123'\n\n"
                    "**🧳 Hành lý:**\n"
                    "• 'Xem hành lý PNR ABC123'\n"
                    "• 'Mua 20kg hành lý PNR ABC123'\n\n"
                    "**🍽️ Suất ăn:**\n"
                    "• 'Xem suất ăn đặc biệt'\n"
                    "• 'Đặt suất ăn VGML PNR ABC123'\n\n"
                    "Bạn cần dịch vụ gì?"
        )],
        "current_agent": "ancillary"
    }
