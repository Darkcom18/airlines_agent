"""
Capability Registry for C1 Travel Agent System.

Quản lý tập trung tất cả capabilities (khả năng) của hệ thống.
Khi thêm/bớt API, chỉ cần sửa status trong file này.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class CapabilityStatus(str, Enum):
    """Trạng thái của capability."""
    AVAILABLE = "available"           # API hoạt động, sẵn sàng sử dụng
    COMING_SOON = "coming_soon"       # Sắp có
    DISABLED = "disabled"             # Tạm tắt (có API nhưng đang disable)
    NOT_IMPLEMENTED = "not_implemented"  # Chưa có API


class Capability(BaseModel):
    """Định nghĩa một capability."""
    id: str
    name: str                         # Tên hiển thị (tiếng Việt)
    description: str                  # Mô tả ngắn
    status: CapabilityStatus
    examples: list[str] = []          # Ví dụ câu hỏi của user
    required_params: list[str] = []   # Params bắt buộc
    handler: Optional[str] = None     # Agent xử lý (flight_agent, booking_agent, chat_agent)


# =============================================================================
# CAPABILITY REGISTRY
# Nguồn duy nhất định nghĩa tất cả capabilities của hệ thống
#
# Khi thêm API mới:
#   1. Thêm capability vào đây với status = AVAILABLE
#   2. Implement handler trong agent tương ứng
#
# Khi tắt API:
#   1. Đổi status = DISABLED
# =============================================================================

CAPABILITIES: dict[str, Capability] = {
    # =========================================================================
    # FLIGHT SEARCH
    # =========================================================================
    "flight_search_oneway": Capability(
        id="flight_search_oneway",
        name="Tìm vé một chiều",
        description="Tìm kiếm vé máy bay một chiều",
        status=CapabilityStatus.AVAILABLE,
        examples=[
            "Tìm vé SGN đi HAN ngày 25/12",
            "Vé từ Sài Gòn ra Hà Nội ngày mai",
            "Bay từ HCM đi Đà Nẵng 1/1/2025"
        ],
        required_params=["origin", "destination", "departure_date"],
        handler="flight_agent"
    ),
    "flight_search_roundtrip": Capability(
        id="flight_search_roundtrip",
        name="Tìm vé khứ hồi",
        description="Tìm kiếm vé máy bay khứ hồi",
        status=CapabilityStatus.AVAILABLE,
        examples=[
            "Vé khứ hồi SGN-DAD 25/12 về 30/12",
            "Tìm vé đi Hà Nội khứ hồi cuối tuần này"
        ],
        required_params=["origin", "destination", "departure_date", "return_date"],
        handler="flight_agent"
    ),
    "flight_search_multicity": Capability(
        id="flight_search_multicity",
        name="Tìm vé nhiều chặng",
        description="Tìm kiếm vé máy bay nhiều chặng",
        status=CapabilityStatus.AVAILABLE,
        examples=[
            "SGN → HAN → DAD → SGN",
            "Vé nhiều chặng Sài Gòn - Hà Nội - Đà Nẵng"
        ],
        required_params=["legs"],
        handler="flight_agent"
    ),
    "price_by_month": Capability(
        id="price_by_month",
        name="Giá vé theo tháng",
        description="Xem giá vé trong khoảng thời gian (không cần ngày cụ thể)",
        status=CapabilityStatus.NOT_IMPLEMENTED,
        examples=[
            "Giá vé đi Đà Nẵng tháng 12",
            "Vé máy bay đi Nhật tháng sau"
        ],
        required_params=["destination", "month"],
        handler="flight_agent"
    ),

    # =========================================================================
    # BOOKING
    # =========================================================================
    "booking_lookup": Capability(
        id="booking_lookup",
        name="Tra cứu booking",
        description="Tra cứu thông tin đặt chỗ theo mã PNR",
        status=CapabilityStatus.NOT_IMPLEMENTED,
        examples=[
            "Tra cứu booking ABC123",
            "Kiểm tra mã đặt chỗ XYZ789"
        ],
        required_params=["pnr_code"],
        handler="booking_agent"
    ),
    "booking_create": Capability(
        id="booking_create",
        name="Đặt vé",
        description="Tạo booking mới",
        status=CapabilityStatus.NOT_IMPLEMENTED,
        examples=[
            "Đặt vé chuyến bay này",
            "Book vé cho tôi"
        ],
        required_params=["flight_id", "passengers"],
        handler="booking_agent"
    ),

    # =========================================================================
    # POLICIES & INFO
    # =========================================================================
    "baggage_policy": Capability(
        id="baggage_policy",
        name="Chính sách hành lý",
        description="Thông tin về hành lý xách tay, ký gửi",
        status=CapabilityStatus.NOT_IMPLEMENTED,
        examples=[
            "Hành lý xách tay bao nhiêu kg?",
            "Quy định hành lý Vietnam Airlines"
        ],
        required_params=[],
        handler="chat_agent"
    ),
    "refund_policy": Capability(
        id="refund_policy",
        name="Chính sách hoàn/đổi vé",
        description="Thông tin về hoàn vé, đổi vé",
        status=CapabilityStatus.NOT_IMPLEMENTED,
        examples=[
            "Hoàn vé như thế nào?",
            "Đổi vé có mất phí không?"
        ],
        required_params=[],
        handler="chat_agent"
    ),

    # =========================================================================
    # GENERAL CHAT
    # =========================================================================
    "general_chat": Capability(
        id="general_chat",
        name="Trò chuyện chung",
        description="Trả lời các câu hỏi chung, chào hỏi",
        status=CapabilityStatus.AVAILABLE,  # Luôn available
        examples=[
            "Xin chào",
            "Bạn có thể giúp gì?"
        ],
        required_params=[],
        handler="chat_agent"
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_capabilities() -> list[Capability]:
    """Lấy tất cả capabilities."""
    return list(CAPABILITIES.values())


def get_available_capabilities() -> list[Capability]:
    """Lấy danh sách capabilities đang available."""
    return [
        cap for cap in CAPABILITIES.values()
        if cap.status == CapabilityStatus.AVAILABLE
    ]


def get_capability(capability_id: str) -> Optional[Capability]:
    """Lấy capability theo ID."""
    return CAPABILITIES.get(capability_id)


def is_capability_available(capability_id: str) -> bool:
    """Kiểm tra capability có available không."""
    cap = CAPABILITIES.get(capability_id)
    return cap is not None and cap.status == CapabilityStatus.AVAILABLE


def get_capability_status(capability_id: str) -> Optional[CapabilityStatus]:
    """Lấy status của capability."""
    cap = CAPABILITIES.get(capability_id)
    return cap.status if cap else None


def get_supported_examples() -> list[str]:
    """Lấy tất cả examples của capabilities available."""
    examples = []
    for cap in get_available_capabilities():
        examples.extend(cap.examples)
    return examples


def get_not_supported_message(capability_id: Optional[str] = None) -> str:
    """
    Tạo message thân thiện cho capability chưa support.

    Args:
        capability_id: ID của capability (optional)

    Returns:
        Message thông báo chưa hỗ trợ
    """
    cap = CAPABILITIES.get(capability_id) if capability_id else None
    cap_name = cap.name if cap else "này"

    # Lấy danh sách những gì đang available
    available = get_available_capabilities()

    if available:
        available_list = "\n".join([f"  • {c.name}" for c in available])
        examples = get_supported_examples()[:2]
        examples_str = "\n".join([f"  - {ex}" for ex in examples]) if examples else ""

        return f"""🚧 **Chức năng "{cap_name}" hiện chưa được hỗ trợ.**

Tôi có thể giúp bạn:
{available_list}

{f"**Ví dụ:**{chr(10)}{examples_str}" if examples_str else ""}"""
    else:
        # Không có capability nào available
        return f"""🚧 **Chức năng "{cap_name}" hiện chưa được hỗ trợ.**

Hệ thống đang trong quá trình phát triển. Vui lòng quay lại sau!

Nếu cần hỗ trợ, bạn có thể liên hệ hotline: 1900-xxxx"""


def get_capability_by_intent(intent: str) -> Optional[str]:
    """
    Map intent sang capability ID.

    Args:
        intent: Intent được detect (flight, booking, chat, etc.)

    Returns:
        Capability ID tương ứng
    """
    # Mapping từ intent -> capability
    # Có thể mở rộng thêm khi cần
    intent_mapping = {
        "flight": "flight_search_oneway",
        "flight_oneway": "flight_search_oneway",
        "flight_roundtrip": "flight_search_roundtrip",
        "flight_multicity": "flight_search_multicity",
        "booking": "booking_lookup",
        "booking_lookup": "booking_lookup",
        "booking_create": "booking_create",
        "baggage": "baggage_policy",
        "refund": "refund_policy",
        "chat": "general_chat",
        "greeting": "general_chat",
    }
    return intent_mapping.get(intent)
