"""
Supervisor Agent for C1 Travel Agent System.
Routes user requests to appropriate specialized agents.
Uses keyword-based routing for reliability.
"""
import re
from datetime import datetime, timedelta
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import structlog

from src.core.llm import get_llm
from .state import AgentState, FlightSearchParams
from .prompts import SUPERVISOR_PROMPT

logger = structlog.get_logger()

# Keywords for intent detection
FLIGHT_KEYWORDS = [
    "vé", "ve", "chuyến bay", "chuyen bay", "flight", "bay",
    "tìm vé", "tim ve", "đặt vé", "dat ve", "giá vé", "gia ve",
    "khứ hồi", "khu hoi", "một chiều", "mot chieu", "roundtrip", "oneway",
    "sgn", "han", "dad", "sài gòn", "sai gon", "hà nội", "ha noi", "đà nẵng", "da nang",
    "hcm", "hn", "đi", "di", "đến", "den", "từ", "tu",
    # Short abbreviations
    "sg", "dn", "sg-hn", "hn-sg", "sg-dn", "dn-sg", "hn-dn", "dn-hn",
    # Common routes
    "sài gòn hà nội", "hà nội sài gòn", "saigon hanoi", "hanoi saigon"
]

# Strong flight indicators (only need 1 match)
FLIGHT_STRONG_KEYWORDS = [
    "chuyến bay", "chuyen bay", "flight", "vé máy bay", "ve may bay",
    "tìm vé", "tim ve", "đặt vé", "dat ve", "giá vé", "gia ve",
    "khứ hồi", "khu hoi", "một chiều", "mot chieu", "roundtrip", "oneway",
    "sg-hn", "hn-sg", "sg-dn", "dn-sg", "sgn-han", "han-sgn"
]

BOOKING_KEYWORDS = [
    "pnr", "booking", "mã đặt", "ma dat", "tra cứu", "tra cuu",
    "kiểm tra", "kiem tra", "đặt chỗ", "dat cho", "giữ chỗ", "giu cho"
]

TICKETING_KEYWORDS = [
    "xuất vé", "xuat ve", "issue ticket", "phát vé", "phat ve",
    "void", "hoàn vé", "hoan ve", "đổi vé", "doi ve", "reissue",
    "số vé", "so ve", "ticket number", "vé điện tử", "ve dien tu",
    "emd", "refund", "hoàn tiền", "hoan tien"
]

PNR_KEYWORDS = [
    "pnr", "booking", "hủy booking", "huy booking", "cancel",
    "hủy chặng", "huy chang", "đổi chuyến", "doi chuyen",
    "thêm hành khách", "them hanh khach", "split", "tách pnr",
    "ssr", "ffn", "frequent flyer", "thẻ thành viên", "the thanh vien",
    "remark", "osi", "cập nhật liên hệ", "cap nhat lien he"
]

ANCILLARY_KEYWORDS = [
    "ghế", "ghe", "seat", "chỗ ngồi", "cho ngoi", "sơ đồ ghế", "so do ghe",
    "hành lý", "hanh ly", "baggage", "luggage", "vali", "túi xách",
    "suất ăn", "suat an", "meal", "đồ ăn", "do an",
    "dịch vụ", "dich vu", "thêm dịch vụ", "them dich vu"
]

GREETING_KEYWORDS = [
    "xin chào", "xin chao", "hello", "hi", "chào", "chao",
    "tạm biệt", "tam biet", "bye", "cảm ơn", "cam on", "thanks"
]

# Chat/consultation keywords - questions that need chat agent, not flight search
CHAT_KEYWORDS = [
    # Weather/season questions
    "mùa nào", "mua nao", "thời tiết", "thoi tiet", "weather", "season",
    "khi nào", "khi nao", "lúc nào", "luc nao", "bao giờ", "bao gio",
    # Travel tips questions
    "đẹp nhất", "dep nhat", "best time", "nên đi", "nen di",
    "thích hợp", "thich hop", "phù hợp", "phu hop",
    "gợi ý", "goi y", "suggest", "recommend", "tư vấn", "tu van",
    # Info questions
    "là gì", "la gi", "what is", "how to", "làm sao", "lam sao",
    "ở đâu", "o dau", "where", "tại sao", "tai sao", "why",
    "bao nhiêu", "bao nhieu", "how much", "how many",
    # Policy questions
    "chính sách", "chinh sach", "policy", "quy định", "quy dinh",
    "hành lý", "hanh ly", "baggage", "luggage", "ký gửi", "ky gui",
    "hoàn vé", "hoan ve", "refund", "đổi vé", "doi ve", "change",
    # General questions (not flight search)
    "có nên", "co nen", "should i", "có được", "co duoc",
    "như thế nào", "nhu the nao", "how", "thế nào", "the nao"
]

# Airport code mapping
AIRPORT_CODES = {
    # Vietnam
    "sài gòn": "SGN", "sai gon": "SGN", "hồ chí minh": "SGN", "ho chi minh": "SGN", "hcm": "SGN", "sg": "SGN", "tân sơn nhất": "SGN",
    "hà nội": "HAN", "ha noi": "HAN", "hn": "HAN", "nội bài": "HAN",
    "đà nẵng": "DAD", "da nang": "DAD", "đn": "DAD", "dn": "DAD",
    "nha trang": "CXR", "cam ranh": "CXR",
    "phú quốc": "PQC", "phu quoc": "PQC",
    "đà lạt": "DLI", "da lat": "DLI",
    "huế": "HUI", "hue": "HUI",
    "hải phòng": "HPH", "hai phong": "HPH",
    "quy nhơn": "UIH", "quy nhon": "UIH",
    # International - Asia
    "bangkok": "BKK", "thái lan": "BKK", "thai lan": "BKK",
    "singapore": "SIN",
    "seoul": "ICN", "incheon": "ICN", "hàn quốc": "ICN", "han quoc": "ICN", "hàn": "ICN", "han": "ICN",
    "tokyo": "NRT", "narita": "NRT", "nhật bản": "NRT", "nhat ban": "NRT", "nhật": "NRT", "nhat": "NRT",
    "osaka": "KIX",
    "hong kong": "HKG", "hồng kông": "HKG", "hong kong": "HKG",
    "taipei": "TPE", "đài loan": "TPE", "dai loan": "TPE", "đài bắc": "TPE",
    "kuala lumpur": "KUL", "malaysia": "KUL",
    "manila": "MNL", "philippines": "MNL",
    "jakarta": "CGK", "indonesia": "CGK",
    "bali": "DPS", "denpasar": "DPS",
    # International - Others
    "paris": "CDG", "pháp": "CDG", "phap": "CDG",
    "london": "LHR", "anh": "LHR",
    "sydney": "SYD", "úc": "SYD", "uc": "SYD", "australia": "SYD",
    "los angeles": "LAX",
    "new york": "JFK",
    "san francisco": "SFO",
}

# Country suggestions when no specific city
COUNTRY_AIRPORTS = {
    "hàn quốc": ["ICN (Seoul/Incheon)", "PUS (Busan)"],
    "han quoc": ["ICN (Seoul/Incheon)", "PUS (Busan)"],
    "hàn": ["ICN (Seoul/Incheon)", "PUS (Busan)"],
    "han": ["ICN (Seoul/Incheon)", "PUS (Busan)"],
    "nhật bản": ["NRT (Tokyo/Narita)", "HND (Tokyo/Haneda)", "KIX (Osaka)", "NGO (Nagoya)"],
    "nhat ban": ["NRT (Tokyo/Narita)", "HND (Tokyo/Haneda)", "KIX (Osaka)", "NGO (Nagoya)"],
    "nhật": ["NRT (Tokyo/Narita)", "HND (Tokyo/Haneda)", "KIX (Osaka)"],
    "nhat": ["NRT (Tokyo/Narita)", "HND (Tokyo/Haneda)", "KIX (Osaka)"],
    "thái lan": ["BKK (Bangkok)", "CNX (Chiang Mai)", "HKT (Phuket)"],
    "thai lan": ["BKK (Bangkok)", "CNX (Chiang Mai)", "HKT (Phuket)"],
    "singapore": ["SIN (Singapore Changi)"],
    "trung quốc": ["PEK (Beijing)", "PVG (Shanghai)", "CAN (Guangzhou)", "SZX (Shenzhen)"],
    "trung quoc": ["PEK (Beijing)", "PVG (Shanghai)", "CAN (Guangzhou)", "SZX (Shenzhen)"],
    "đài loan": ["TPE (Taipei)", "KHH (Kaohsiung)"],
    "dai loan": ["TPE (Taipei)", "KHH (Kaohsiung)"],
    "malaysia": ["KUL (Kuala Lumpur)", "PEN (Penang)"],
    "indonesia": ["CGK (Jakarta)", "DPS (Bali)"],
    "úc": ["SYD (Sydney)", "MEL (Melbourne)", "BNE (Brisbane)"],
    "uc": ["SYD (Sydney)", "MEL (Melbourne)", "BNE (Brisbane)"],
    "australia": ["SYD (Sydney)", "MEL (Melbourne)", "BNE (Brisbane)"],
    "mỹ": ["LAX (Los Angeles)", "SFO (San Francisco)", "JFK (New York)"],
    "my": ["LAX (Los Angeles)", "SFO (San Francisco)", "JFK (New York)"],
    "pháp": ["CDG (Paris)", "NCE (Nice)"],
    "phap": ["CDG (Paris)", "NCE (Nice)"],
    "anh": ["LHR (London Heathrow)", "LGW (London Gatwick)"],
}


def detect_intent(message: str, state: "AgentState" = None) -> str:
    """Detect user intent based on keywords and conversation context."""
    msg_lower = message.lower()

    # Check for ticketing keywords (highest priority - specific actions)
    ticketing_score = sum(1 for kw in TICKETING_KEYWORDS if kw in msg_lower)
    if ticketing_score >= 1:
        return "ticketing"

    # Check for ancillary keywords (seat, baggage, meal)
    ancillary_score = sum(1 for kw in ANCILLARY_KEYWORDS if kw in msg_lower)
    if ancillary_score >= 1:
        return "ancillary"

    # Check for PNR management keywords
    pnr_score = sum(1 for kw in PNR_KEYWORDS if kw in msg_lower)
    if pnr_score >= 2:
        return "pnr"

    # Check for strong flight indicators FIRST (only need 1)
    # These are unambiguous flight search requests
    if any(kw in msg_lower for kw in FLIGHT_STRONG_KEYWORDS):
        return "flight"

    # Check for chat/consultation keywords - these override weak flight keywords
    # Questions like "mùa nào đi HN đẹp nhất?" should go to chat, not flight
    chat_score = sum(1 for kw in CHAT_KEYWORDS if kw in msg_lower)
    if chat_score >= 1:
        # Has chat keyword - this is likely a question, not a flight search
        return "chat"

    # Check for booking keywords
    booking_score = sum(1 for kw in BOOKING_KEYWORDS if kw in msg_lower)
    if booking_score >= 2:
        return "booking"

    # Check for flight-related keywords (need 2 for weaker keywords)
    flight_score = sum(1 for kw in FLIGHT_KEYWORDS if kw in msg_lower)
    if flight_score >= 2:
        return "flight"

    # Check if there's existing flight search context
    # If user says "tiếp đi", "xử lý đi", etc. and we have flight params -> continue flight
    if state and state.flight_search:
        if state.flight_search.origin or state.flight_search.destination:
            continue_keywords = ["tiếp", "tiep", "xử lý", "xu ly", "đi", "di", "ok", "được", "duoc", "yes", "vâng", "vang"]
            if any(kw in msg_lower for kw in continue_keywords):
                return "flight"

    # Check for greeting/ending
    if any(kw in msg_lower for kw in ["tạm biệt", "bye", "goodbye"]):
        return "end"

    return "chat"


def extract_flight_params(message: str) -> dict:
    """Extract flight search parameters from message."""
    msg_lower = message.lower()
    params = {}
    country_suggestions = []

    # PRIORITY 0: Check for route patterns like "sg-hn", "hn-sg", "sgn-han"
    route_pattern = r'(sg|hn|dn|sgn|han|dad|hcm)[\s\-]+(sg|hn|dn|sgn|han|dad|hcm)'
    route_match = re.search(route_pattern, msg_lower)
    if route_match:
        abbrev_map = {
            "sg": "SGN", "sgn": "SGN", "hcm": "SGN",
            "hn": "HAN", "han": "HAN",
            "dn": "DAD", "dad": "DAD"
        }
        origin = abbrev_map.get(route_match.group(1).lower())
        dest = abbrev_map.get(route_match.group(2).lower())
        if origin and dest:
            params["origin"] = origin
            params["destination"] = dest

    # PRIORITY 1: Check for IATA airport codes (most reliable, case-insensitive)
    if "origin" not in params or "destination" not in params:
        code_pattern = r'\b(SGN|HAN|DAD|CXR|PQC|DLI|HUI|HPH|UIH|VCA|BMV|BKK|SIN|ICN|NRT|KIX|HKG|TPE|KUL|MNL|CGK|DPS|CDG|LHR|SYD|LAX|JFK|SFO)\b'
        codes = re.findall(code_pattern, message.upper())
        if len(codes) >= 2:
            params["origin"] = codes[0]
            params["destination"] = codes[1]
        elif len(codes) == 1:
            if "origin" not in params:
                params["origin"] = codes[0]
            elif "destination" not in params:
                params["destination"] = codes[0]

    # PRIORITY 2: If still missing params, try city names
    if "origin" not in params or "destination" not in params:
        # Find all cities mentioned and their positions
        found_cities = []
        for name, code in AIRPORT_CODES.items():
            # Skip short ambiguous names when parsing city names
            if name in ["han", "hàn", "hn", "hcm", "đn", "sg", "dn"]:
                continue

            idx = msg_lower.find(name)
            if idx != -1:
                found_cities.append((idx, name, code))

        # Sort by position
        found_cities.sort(key=lambda x: x[0])

        # Extract airports based on context
        for idx, name, code in found_cities:
            before = msg_lower[:idx]

            # Check context words before city name
            is_origin = any(w in before[-15:] for w in ["từ ", "tu ", "đi từ", "di tu", "khởi hành", "xuất phát"])
            is_dest = any(w in before[-10:] for w in ["đi ", "di ", "đến ", "den ", "tới ", "ra ", "vào "])

            if is_origin and "origin" not in params:
                params["origin"] = code
            elif is_dest and "destination" not in params:
                params["destination"] = code
            elif "origin" not in params:
                params["origin"] = code
            elif "destination" not in params:
                params["destination"] = code

    # PRIORITY 3: Check for country names (only if still missing destination)
    if "destination" not in params:
        for country, airports in COUNTRY_AIRPORTS.items():
            if country in msg_lower:
                country_suggestions.append({
                    "country": country,
                    "airports": airports
                })

    # Extract date - try relative dates first, then explicit dates
    today = datetime.now()

    # Check for relative date keywords
    relative_dates = {
        "hôm nay": 0, "hom nay": 0, "today": 0,
        "ngày mai": 1, "ngay mai": 1, "mai": 1, "tomorrow": 1,
        "ngày kia": 2, "ngay kia": 2, "mốt": 2, "mot": 2,
        "tuần sau": 7, "tuan sau": 7, "next week": 7,
        "cuối tuần": (5 - today.weekday()) % 7 or 7,  # Next Saturday
        "cuoi tuan": (5 - today.weekday()) % 7 or 7,
    }

    for keyword, days_offset in relative_dates.items():
        if keyword in msg_lower:
            target_date = today + timedelta(days=days_offset)
            params["departure_date"] = target_date.strftime("%Y-%m-%d")
            break

    # If no relative date found, try explicit date patterns
    if "departure_date" not in params:
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY-MM-DD
            r'ngày\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # ngày DD/MM/YYYY
            r'(\d{1,2})[/-](\d{1,2})',  # DD/MM (assume current year)
        ]

        for pattern in date_patterns:
            match = re.search(pattern, message)
            if match:
                groups = match.groups()
                if len(groups) == 2:  # DD/MM only
                    year = today.year
                    month = int(groups[1])
                    day = int(groups[0])
                    # If date already passed this year, use next year
                    target = datetime(year, month, day)
                    if target < today:
                        target = datetime(year + 1, month, day)
                    params["departure_date"] = target.strftime("%Y-%m-%d")
                elif len(groups[0]) == 4:  # YYYY-MM-DD
                    params["departure_date"] = f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                else:  # DD/MM/YYYY
                    params["departure_date"] = f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
                break

    # Extract passenger count
    pax_match = re.search(r'(\d+)\s*(người|nguoi|khách|khach|pax|người lớn)', msg_lower)
    if pax_match:
        params["adults"] = int(pax_match.group(1))
    else:
        params["adults"] = 1

    # Detect roundtrip
    if any(w in msg_lower for w in ["khứ hồi", "khu hoi", "roundtrip", "round trip", "về"]):
        params["search_type"] = "roundtrip"
    else:
        params["search_type"] = "oneway"

    # Add country suggestions if detected
    if country_suggestions:
        params["country_suggestions"] = country_suggestions

    return params


async def supervisor_node(state: AgentState) -> dict:
    """
    Supervisor node that analyzes user intent and routes to appropriate agent.
    Uses keyword-based detection for reliability.
    """
    logger.info("Supervisor analyzing request")

    messages = state.messages
    if not messages:
        return {
            "next_agent": "chat",
            "intent": "greeting"
        }

    # Get the last user message
    last_message = messages[-1]
    if isinstance(last_message, AIMessage):
        # If last message is AI, check the one before
        user_messages = [m for m in messages if isinstance(m, HumanMessage)]
        if not user_messages:
            return {"next_agent": "chat", "intent": "no_user_message"}
        last_message = user_messages[-1]

    user_text = last_message.content

    # Detect intent using keywords and conversation context
    intent = detect_intent(user_text, state)

    logger.info(f"Supervisor detected intent: {intent}", message=user_text[:50])

    updates = {
        "next_agent": intent,
        "intent": intent
    }

    # Extract flight params if going to flight agent
    if intent == "flight":
        flight_params = extract_flight_params(user_text)
        logger.info(f"Extracted flight params: {flight_params}")

        updates["flight_search"] = FlightSearchParams(
            origin=flight_params.get("origin"),
            destination=flight_params.get("destination"),
            departure_date=flight_params.get("departure_date"),
            return_date=flight_params.get("return_date"),
            adults=flight_params.get("adults", 1),
            children=flight_params.get("children", 0),
            infants=flight_params.get("infants", 0),
            search_type=flight_params.get("search_type", "oneway"),
            cabin_class=flight_params.get("cabin_class", "ECONOMY")
        )

    return updates


def should_continue(state: AgentState) -> str:
    """Determine next step in the graph based on supervisor decision."""
    next_agent = state.next_agent

    if next_agent == "end":
        return "end"
    elif next_agent == "chat":
        return "chat_agent"
    elif next_agent == "flight":
        return "flight_agent"
    elif next_agent == "booking":
        return "booking_agent"
    elif next_agent == "ticketing":
        return "ticketing_agent"
    elif next_agent == "pnr":
        return "pnr_agent"
    elif next_agent == "ancillary":
        return "ancillary_agent"
    else:
        return "chat_agent"
