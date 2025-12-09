"""
PNR Agent for C1 Travel Agent System.
Handles PNR retrieval, modification, and management.
"""
import re
from langchain_core.messages import AIMessage
import structlog

from src.mcp_server.tools import get_registry
from src.core.capabilities import is_capability_available, get_not_supported_message
from .state import AgentState

logger = structlog.get_logger()


def format_pnr_details(result: dict) -> str:
    """Format PNR details for display."""
    if not result.get("success") and result.get("error"):
        return f"❌ Không thể tra cứu PNR: {result.get('error')}"

    lines = [
        "📋 **THÔNG TIN ĐẶT CHỖ (PNR)**",
        "",
        f"🔖 Mã booking: **{result.get('booking_code', 'N/A')}**",
        f"📊 Trạng thái: {result.get('status', 'UNKNOWN')}",
        ""
    ]

    # Segments/Flights
    segments = result.get("segments", [])
    if segments:
        lines.append("✈️ **Hành trình:**")
        for i, seg in enumerate(segments, 1):
            lines.append(
                f"   {i}. {seg.get('airline', '')} {seg.get('flight_number', '')} | "
                f"{seg.get('origin', '')} → {seg.get('destination', '')}"
            )
            lines.append(
                f"      📅 {seg.get('departure_date', '')} | "
                f"🕐 {seg.get('departure_time', '')} - {seg.get('arrival_time', '')}"
            )
        lines.append("")

    # Passengers
    passengers = result.get("passengers", [])
    if passengers:
        lines.append("👥 **Hành khách:**")
        for i, pax in enumerate(passengers, 1):
            name = f"{pax.get('title', '')} {pax.get('first_name', '')} {pax.get('last_name', '')}"
            pax_type = pax.get("type", "ADT")
            lines.append(f"   {i}. {name.strip()} ({pax_type})")
        lines.append("")

    # Tickets
    tickets = result.get("tickets", [])
    if tickets:
        lines.append("🎫 **Vé đã xuất:**")
        for ticket in tickets:
            lines.append(f"   • {ticket.get('ticket_number', 'N/A')} - {ticket.get('status', '')}")
        lines.append("")

    # Contact
    contact = result.get("contact", {})
    if contact:
        lines.append("📞 **Liên hệ:**")
        if contact.get("email"):
            lines.append(f"   Email: {contact['email']}")
        if contact.get("phone"):
            lines.append(f"   Phone: {contact['phone']}")
        lines.append("")

    # Time limit
    time_limit = result.get("time_limit")
    if time_limit:
        lines.append(f"⏰ **Hạn xuất vé:** {time_limit}")

    return "\n".join(lines)


async def pnr_agent_node(state: AgentState) -> dict:
    """
    PNR agent for managing bookings and reservations.
    """
    logger.info("PNR agent processing request")

    messages = state.messages
    if not messages:
        return {
            "messages": [AIMessage(
                content="Bạn cần hỗ trợ gì về PNR? Tôi có thể:\n"
                        "• Tra cứu thông tin đặt chỗ\n"
                        "• Hủy booking/hủy chặng\n"
                        "• Đổi chuyến bay\n"
                        "• Cập nhật thông tin hành khách\n"
                        "• Thêm dịch vụ đặc biệt (SSR)\n"
                        "• Thêm số thẻ thành viên bay"
            )],
            "current_agent": "pnr"
        }

    last_message = messages[-1].content.lower()
    registry = get_registry()

    # Check capability
    if not is_capability_available("pnr_management"):
        return {
            "messages": [AIMessage(content=get_not_supported_message("pnr_management"))],
            "current_agent": "pnr"
        }

    # Extract PNR code if present
    pnr_match = re.search(r'\b[A-Z0-9]{6}\b', messages[-1].content)
    pnr_code = pnr_match.group() if pnr_match else None

    # Detect intent
    if any(kw in last_message for kw in ["tra cứu", "xem", "kiểm tra", "retrieve"]):
        if pnr_code:
            result = await registry.call("retrieve_pnr", {
                "booking_code": pnr_code
            })
            response = format_pnr_details(result)
        else:
            response = (
                "Vui lòng cung cấp mã booking (PNR) 6 ký tự.\n\n"
                "Ví dụ: 'Tra cứu PNR ABC123'"
            )

        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "pnr"
        }

    elif any(kw in last_message for kw in ["hủy", "cancel"]):
        if "chặng" in last_message or "segment" in last_message:
            # Cancel segment
            if pnr_code:
                # Try to extract segment index
                seg_match = re.search(r'chặng\s*(\d+)', last_message)
                segment_index = int(seg_match.group(1)) - 1 if seg_match else 0

                result = await registry.call("cancel_segment", {
                    "booking_code": pnr_code,
                    "segment_index": segment_index
                })

                if result.get("success"):
                    response = f"✅ Đã hủy chặng {segment_index + 1} trong PNR {pnr_code}"
                else:
                    response = f"❌ Không thể hủy chặng: {result.get('message', 'Lỗi')}"
            else:
                response = "Vui lòng cung cấp mã PNR và số chặng cần hủy.\n\nVí dụ: 'Hủy chặng 2 PNR ABC123'"
        else:
            # Cancel entire PNR
            if pnr_code:
                result = await registry.call("cancel_pnr", {
                    "booking_code": pnr_code,
                    "reason": "Customer request"
                })

                if result.get("success"):
                    response = f"✅ Đã hủy booking {pnr_code} thành công."
                else:
                    response = f"❌ Không thể hủy booking: {result.get('message', 'Lỗi')}"
            else:
                response = "Vui lòng cung cấp mã PNR cần hủy.\n\nVí dụ: 'Hủy booking ABC123'"

        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "pnr"
        }

    elif any(kw in last_message for kw in ["đổi chuyến", "change flight", "thay đổi chuyến"]):
        if pnr_code:
            response = (
                f"Để đổi chuyến bay cho PNR **{pnr_code}**, tôi cần:\n"
                f"1. Tìm chuyến bay mới (cho tôi biết ngày và tuyến)\n"
                f"2. Chọn chặng cần đổi\n\n"
                f"Bạn muốn đổi sang ngày nào?"
            )
        else:
            response = "Vui lòng cung cấp mã PNR và thông tin chuyến bay mới."

        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "pnr"
        }

    elif any(kw in last_message for kw in ["cập nhật", "update", "sửa"]):
        if "email" in last_message or "phone" in last_message or "liên hệ" in last_message:
            if pnr_code:
                # Extract email/phone if present
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', messages[-1].content)
                phone_match = re.search(r'[\d\s\+\-]{8,15}', messages[-1].content)

                update_args = {"booking_code": pnr_code}
                if email_match:
                    update_args["email"] = email_match.group()
                if phone_match:
                    update_args["phone"] = phone_match.group().strip()

                if email_match or phone_match:
                    result = await registry.call("update_contact", update_args)
                    if result.get("success"):
                        response = f"✅ Đã cập nhật thông tin liên hệ cho PNR {pnr_code}"
                    else:
                        response = f"❌ Không thể cập nhật: {result.get('message')}"
                else:
                    response = "Vui lòng cung cấp email hoặc số điện thoại mới."
            else:
                response = "Vui lòng cung cấp mã PNR và thông tin cần cập nhật."

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "pnr"
            }

    elif any(kw in last_message for kw in ["thẻ thành viên", "frequent flyer", "ff", "ffn"]):
        if pnr_code:
            # Extract FF number
            ff_match = re.search(r'[A-Z]{2}\s*\d{6,12}', messages[-1].content.upper())

            if ff_match:
                ff_parts = ff_match.group().split()
                airline_code = ff_parts[0][:2]
                ff_number = "".join(ff_parts[0][2:] if len(ff_parts) == 1 else ff_parts[1:])

                result = await registry.call("add_frequent_flyer", {
                    "booking_code": pnr_code,
                    "passenger_index": 0,  # First passenger by default
                    "airline_code": airline_code,
                    "ff_number": ff_number
                })

                if result.get("success"):
                    response = f"✅ Đã thêm số thẻ thành viên {airline_code} vào PNR {pnr_code}"
                else:
                    response = f"❌ Không thể thêm: {result.get('message')}"
            else:
                response = (
                    "Vui lòng cung cấp số thẻ thành viên bay.\n\n"
                    "Ví dụ: 'Thêm FFN VN123456789 vào PNR ABC123'"
                )
        else:
            response = "Vui lòng cung cấp mã PNR và số thẻ thành viên."

        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "pnr"
        }

    elif any(kw in last_message for kw in ["ssr", "dịch vụ đặc biệt", "wheelchair", "meal"]):
        if pnr_code:
            response = (
                f"Các dịch vụ đặc biệt (SSR) có thể thêm cho PNR **{pnr_code}**:\n\n"
                f"• **WCHR** - Xe lăn\n"
                f"• **BLND** - Khách khiếm thị\n"
                f"• **DEAF** - Khách khiếm thính\n"
                f"• **MEDA** - Cần hỗ trợ y tế\n"
                f"• **PETC** - Thú cưng trong cabin\n\n"
                f"Bạn cần thêm dịch vụ nào?"
            )
        else:
            response = "Vui lòng cung cấp mã PNR để thêm dịch vụ đặc biệt."

        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "pnr"
        }

    elif any(kw in last_message for kw in ["lịch sử", "history", "changelog"]):
        if pnr_code:
            result = await registry.call("get_pnr_history", {
                "booking_code": pnr_code
            })

            history = result.get("history", [])
            if history:
                lines = [f"📜 **Lịch sử thay đổi PNR {pnr_code}:**", ""]
                for entry in history[:10]:
                    lines.append(f"• {entry.get('timestamp', '')} - {entry.get('action', '')}")
                response = "\n".join(lines)
            else:
                response = f"Không có lịch sử thay đổi cho PNR {pnr_code}"
        else:
            response = "Vui lòng cung cấp mã PNR để xem lịch sử."

        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "pnr"
        }

    else:
        # Default help
        return {
            "messages": [AIMessage(
                content="📋 **Quản lý PNR**\n\n"
                        "Tôi có thể hỗ trợ:\n"
                        "• **Tra cứu** - Xem thông tin đặt chỗ\n"
                        "• **Hủy booking** - Hủy toàn bộ hoặc từng chặng\n"
                        "• **Đổi chuyến** - Thay đổi ngày/chuyến bay\n"
                        "• **Cập nhật liên hệ** - Email, điện thoại\n"
                        "• **Thêm FFN** - Số thẻ thành viên bay\n"
                        "• **SSR** - Dịch vụ đặc biệt\n\n"
                        "Vui lòng cho biết mã PNR và yêu cầu của bạn."
            )],
            "current_agent": "pnr"
        }
