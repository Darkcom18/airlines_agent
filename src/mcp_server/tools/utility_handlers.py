"""
MCP Utility Tool Handlers for C1 Travel Agent System.
Handles airports, airlines, currencies, time utilities.
"""
from typing import Any
import json
from pathlib import Path
import structlog
from mcp.types import Tool

logger = structlog.get_logger()

# Load airports data
AIRPORTS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "airports.json"
AIRPORTS_DATA = {}
if AIRPORTS_FILE.exists():
    with open(AIRPORTS_FILE, "r", encoding="utf-8") as f:
        AIRPORTS_DATA = json.load(f)


# Utility Tools (4 APIs)
UTILITY_TOOLS: dict[str, Tool] = {
    "lookup_airport": Tool(
        name="lookup_airport",
        description="Look up airport information by code or city name",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Airport code (SGN, HAN) or city name (Ho Chi Minh, Hanoi)"
                }
            },
            "required": ["query"]
        }
    ),
    "lookup_airline": Tool(
        name="lookup_airline",
        description="Look up airline information by code",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "2-letter IATA airline code (VN, VJ, QH)"
                }
            },
            "required": ["code"]
        }
    ),
    "convert_currency": Tool(
        name="convert_currency",
        description="Convert between currencies (VND, USD, EUR)",
        inputSchema={
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "from_currency": {"type": "string", "default": "VND"},
                "to_currency": {"type": "string", "default": "USD"}
            },
            "required": ["amount"]
        }
    ),
    "get_flight_duration": Tool(
        name="get_flight_duration",
        description="Calculate flight duration between airports",
        inputSchema={
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "destination": {"type": "string"}
            },
            "required": ["origin", "destination"]
        }
    )
}

# Airline data
AIRLINES = {
    "VN": {"name": "Vietnam Airlines", "country": "Vietnam", "alliance": "SkyTeam", "hub": "SGN/HAN"},
    "VJ": {"name": "VietJet Air", "country": "Vietnam", "alliance": "None", "hub": "SGN/HAN"},
    "QH": {"name": "Bamboo Airways", "country": "Vietnam", "alliance": "None", "hub": "HAN"},
    "BL": {"name": "Pacific Airlines", "country": "Vietnam", "alliance": "None", "hub": "SGN"},
    "VU": {"name": "Vietravel Airlines", "country": "Vietnam", "alliance": "None", "hub": "SGN"},
    "SQ": {"name": "Singapore Airlines", "country": "Singapore", "alliance": "Star Alliance", "hub": "SIN"},
    "TG": {"name": "Thai Airways", "country": "Thailand", "alliance": "Star Alliance", "hub": "BKK"},
    "CX": {"name": "Cathay Pacific", "country": "Hong Kong", "alliance": "Oneworld", "hub": "HKG"},
    "KE": {"name": "Korean Air", "country": "South Korea", "alliance": "SkyTeam", "hub": "ICN"},
    "JL": {"name": "Japan Airlines", "country": "Japan", "alliance": "Oneworld", "hub": "NRT/HND"},
    "NH": {"name": "All Nippon Airways", "country": "Japan", "alliance": "Star Alliance", "hub": "NRT/HND"},
    "MH": {"name": "Malaysia Airlines", "country": "Malaysia", "alliance": "Oneworld", "hub": "KUL"},
    "GA": {"name": "Garuda Indonesia", "country": "Indonesia", "alliance": "SkyTeam", "hub": "CGK"},
    "PR": {"name": "Philippine Airlines", "country": "Philippines", "alliance": "None", "hub": "MNL"}
}

# Exchange rates (approximate)
EXCHANGE_RATES = {
    "VND": 1,
    "USD": 24500,
    "EUR": 26500,
    "JPY": 165,
    "KRW": 18,
    "SGD": 18200,
    "THB": 680,
    "MYR": 5200,
    "CNY": 3400
}

# Flight durations (approximate in minutes)
FLIGHT_DURATIONS = {
    ("SGN", "HAN"): 125,
    ("SGN", "DAD"): 80,
    ("HAN", "DAD"): 75,
    ("SGN", "SIN"): 120,
    ("SGN", "BKK"): 95,
    ("SGN", "HKG"): 150,
    ("SGN", "ICN"): 300,
    ("SGN", "NRT"): 360,
    ("HAN", "SIN"): 190,
    ("HAN", "BKK"): 120,
    ("HAN", "ICN"): 240,
    ("HAN", "NRT"): 300
}


async def handle_utility_tool(name: str, arguments: dict) -> dict:
    """Handle utility tool calls."""
    try:
        if name == "lookup_airport":
            query = arguments["query"].upper().strip()

            # Search by code first
            if query in AIRPORTS_DATA:
                airport = AIRPORTS_DATA[query]
                return {
                    "found": True,
                    "code": query,
                    "name": airport.get("name"),
                    "city": airport.get("city"),
                    "country": airport.get("country"),
                    "timezone": airport.get("timezone")
                }

            # Search by city name
            for code, airport in AIRPORTS_DATA.items():
                city = airport.get("city", "").upper()
                name_field = airport.get("name", "").upper()
                if query in city or query in name_field:
                    return {
                        "found": True,
                        "code": code,
                        "name": airport.get("name"),
                        "city": airport.get("city"),
                        "country": airport.get("country"),
                        "timezone": airport.get("timezone")
                    }

            return {"found": False, "query": arguments["query"]}

        elif name == "lookup_airline":
            code = arguments["code"].upper()
            if code in AIRLINES:
                airline = AIRLINES[code]
                return {
                    "found": True,
                    "code": code,
                    "name": airline["name"],
                    "country": airline["country"],
                    "alliance": airline["alliance"],
                    "hub": airline["hub"]
                }
            return {"found": False, "code": code}

        elif name == "convert_currency":
            amount = arguments["amount"]
            from_curr = arguments.get("from_currency", "VND").upper()
            to_curr = arguments.get("to_currency", "USD").upper()

            if from_curr not in EXCHANGE_RATES:
                return {"error": f"Unknown currency: {from_curr}"}
            if to_curr not in EXCHANGE_RATES:
                return {"error": f"Unknown currency: {to_curr}"}

            # Convert to VND first, then to target
            vnd_amount = amount * EXCHANGE_RATES[from_curr]
            result = vnd_amount / EXCHANGE_RATES[to_curr]

            return {
                "original_amount": amount,
                "from_currency": from_curr,
                "to_currency": to_curr,
                "converted_amount": round(result, 2),
                "exchange_rate": EXCHANGE_RATES[from_curr] / EXCHANGE_RATES[to_curr]
            }

        elif name == "get_flight_duration":
            origin = arguments["origin"].upper()
            destination = arguments["destination"].upper()

            # Check both directions
            duration = FLIGHT_DURATIONS.get((origin, destination))
            if not duration:
                duration = FLIGHT_DURATIONS.get((destination, origin))

            if duration:
                hours = duration // 60
                minutes = duration % 60
                return {
                    "origin": origin,
                    "destination": destination,
                    "duration_minutes": duration,
                    "duration_formatted": f"{hours}h {minutes}m" if hours else f"{minutes}m",
                    "approximate": True
                }
            else:
                return {
                    "origin": origin,
                    "destination": destination,
                    "duration_minutes": None,
                    "message": "Flight duration not available for this route"
                }

        else:
            return {"error": f"Unknown utility tool: {name}"}

    except Exception as e:
        logger.error(f"Utility tool error: {e}")
        return {"error": str(e)}
