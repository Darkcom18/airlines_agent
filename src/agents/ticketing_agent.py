"""
Ticketing Agent for C1 Travel Agent System.
Handles ticket issuance, void, reissue, and EMD operations.
"""
import re
from langchain_core.messages import AIMessage
import structlog

from src.mcp_server.tools import get_registry
from src.core.capabilities import is_capability_available, get_not_supported_message
from .state import AgentState

logger = structlog.get_logger()


async def ticketing_agent_node(state: AgentState) -> dict:
    """
    Ticketing agent for issuing and managing tickets.
    """
    logger.info("Ticketing agent processing request")

    messages = state.messages
    if not messages:
        return {
            "messages": [AIMessage(
                content="Bạn cần hỗ trợ về xuất vé gì? Tôi có thể giúp:\n"
                        "• Xuất vé (issue ticket)\n"
                        "• Hoàn vé (void ticket trong 24h)\n"
                        "• Đổi vé (reissue)\n"
                        "• Kiểm tra trạng thái vé"
            )],
            "current_agent": "ticketing"
        }

    last_message = messages[-1].content.lower()

    # Check capability
    if not is_capability_available("ticketing"):
        return {
            "messages": [AIMessage(content=get_not_supported_message("ticketing"))],
            "current_agent": "ticketing"
        }

    registry = get_registry()

    # Detect intent from message
    if any(kw in last_message for kw in ["xuất vé", "issue", "phát vé"]):
        # Issue ticket flow
        pnr_match = re.search(r'\b[A-Z0-9]{6}\b', messages[-1].content)

        if pnr_match:
            pnr_code = pnr_match.group()
            logger.info("Issuing ticket for PNR", pnr=pnr_code)

            result = await registry.call("issue_ticket", {
                "booking_code": pnr_code,
                "payment_method": "AGENT_CREDIT"
            })

            if result.get("success"):
                response = (
                    f"✅ **Xuất vé thành công!**\n\n"
                    f"🔖 Mã booking: **{pnr_code}**\n"
                    f"🎫 Số vé: **{result.get('ticket_number', 'N/A')}**\n"
                    f"📅 Thời gian: {result.get('issued_at', 'N/A')}\n\n"
                    f"💡 Vé đã được gửi qua email đăng ký."
                )
            else:
                response = f"❌ Không thể xuất vé: {result.get('message', result.get('error', 'Lỗi không xác định'))}"

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ticketing"
            }
        else:
            return {
                "messages": [AIMessage(
                    content="Vui lòng cung cấp mã booking (PNR) 6 ký tự để xuất vé.\n\n"
                            "Ví dụ: 'Xuất vé ABC123'"
                )],
                "current_agent": "ticketing"
            }

    elif any(kw in last_message for kw in ["void", "hoàn", "hủy vé"]):
        # Void ticket flow
        ticket_match = re.search(r'\b\d{13}\b', messages[-1].content)
        pnr_match = re.search(r'\b[A-Z0-9]{6}\b', messages[-1].content)

        if ticket_match and pnr_match:
            ticket_number = ticket_match.group()
            pnr_code = pnr_match.group()

            result = await registry.call("void_ticket", {
                "ticket_number": ticket_number,
                "booking_code": pnr_code,
                "reason": "Customer request"
            })

            if result.get("success"):
                response = (
                    f"✅ **Void vé thành công!**\n\n"
                    f"🎫 Số vé: {ticket_number}\n"
                    f"📊 Trạng thái: VOIDED"
                )
            else:
                response = f"❌ Không thể void vé: {result.get('message', 'Vé đã quá thời hạn void (24h)')}"

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ticketing"
            }
        else:
            return {
                "messages": [AIMessage(
                    content="Để void vé, tôi cần:\n"
                            "• Số vé (13 chữ số)\n"
                            "• Mã booking (6 ký tự)\n\n"
                            "Ví dụ: 'Void vé 7381234567890 PNR ABC123'"
                )],
                "current_agent": "ticketing"
            }

    elif any(kw in last_message for kw in ["đổi vé", "reissue", "thay đổi"]):
        # Reissue flow
        return {
            "messages": [AIMessage(
                content="Để đổi vé, tôi cần:\n"
                        "1. Số vé hiện tại (13 chữ số)\n"
                        "2. Mã booking (PNR 6 ký tự)\n"
                        "3. Chuyến bay mới (cần tìm kiếm trước)\n\n"
                        "Lưu ý: Có thể phát sinh phí đổi vé và chênh lệch giá vé."
            )],
            "current_agent": "ticketing"
        }

    elif any(kw in last_message for kw in ["kiểm tra", "trạng thái", "status"]):
        # Check ticket status
        ticket_match = re.search(r'\b\d{13}\b', messages[-1].content)

        if ticket_match:
            ticket_number = ticket_match.group()

            result = await registry.call("get_ticket_status", {
                "ticket_number": ticket_number
            })

            response = (
                f"🎫 **Thông tin vé**\n\n"
                f"Số vé: {ticket_number}\n"
                f"Trạng thái: {result.get('status', 'UNKNOWN')}\n"
                f"Ngày xuất: {result.get('issued_date', 'N/A')}\n"
                f"Hành khách: {result.get('passenger_name', 'N/A')}"
            )

            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "ticketing"
            }
        else:
            return {
                "messages": [AIMessage(
                    content="Vui lòng cung cấp số vé 13 chữ số để kiểm tra.\n\n"
                            "Ví dụ: 'Kiểm tra vé 7381234567890'"
                )],
                "current_agent": "ticketing"
            }

    elif any(kw in last_message for kw in ["refund", "hoàn tiền"]):
        # Refund flow
        return {
            "messages": [AIMessage(
                content="Để yêu cầu hoàn tiền vé, tôi cần:\n"
                        "• Số vé (13 chữ số)\n"
                        "• Mã booking (PNR)\n"
                        "• Lý do hoàn (tự nguyện/không tự nguyện)\n\n"
                        "Lưu ý: Phí hoàn vé phụ thuộc vào loại vé và thời điểm yêu cầu."
            )],
            "current_agent": "ticketing"
        }

    else:
        # Default help
        return {
            "messages": [AIMessage(
                content="🎫 **Dịch vụ xuất vé**\n\n"
                        "Tôi có thể hỗ trợ:\n"
                        "• **Xuất vé** - Cần mã booking (PNR)\n"
                        "• **Void vé** - Trong vòng 24h từ khi xuất\n"
                        "• **Đổi vé** - Thay đổi ngày/chuyến bay\n"
                        "• **Kiểm tra vé** - Xem trạng thái vé\n"
                        "• **Hoàn tiền** - Yêu cầu refund\n\n"
                        "Bạn cần hỗ trợ gì?"
            )],
            "current_agent": "ticketing"
        }
