"""
Flight Agent for C1 Travel Agent System.
Handles flight search and comparison across multiple sources.
"""
import asyncio
from typing import Optional

from langchain_core.messages import AIMessage
import structlog

from src.mcp_server.api_client.sftech import SFTechClient
from src.core.capabilities import (
    is_capability_available,
    get_not_supported_message,
)
from .state import AgentState, FlightSearchResult

logger = structlog.get_logger()

# All available API sources
API_SOURCES = ["F1", "F10", "VJ"]


async def search_single_source(source: str, params: dict) -> dict:
    """Execute flight search for a single source."""
    client = SFTechClient(source=source)

    try:
        search_type = params.get("search_type", "oneway")

        if search_type == "roundtrip":
            result = await client.search_roundtrip_flights(
                origin=params["origin"],
                destination=params["destination"],
                departure_date=params["departure_date"],
                return_date=params["return_date"],
                adults=params.get("adults", 1),
                children=params.get("children", 0),
                infants=params.get("infants", 0),
                cabin_class=params.get("cabin_class", "ECONOMY")
            )
        elif search_type == "multicity":
            result = await client.search_multicity_flights(
                legs=params["legs"],
                adults=params.get("adults", 1),
                children=params.get("children", 0),
                infants=params.get("infants", 0),
                cabin_class=params.get("cabin_class", "ECONOMY")
            )
        else:  # oneway
            result = await client.search_oneway_flights(
                origin=params["origin"],
                destination=params["destination"],
                departure_date=params["departure_date"],
                adults=params.get("adults", 1),
                children=params.get("children", 0),
                infants=params.get("infants", 0),
                cabin_class=params.get("cabin_class", "ECONOMY")
            )

        flights = [
            {
                "id": f.id,
                "source": source,  # Mark with source
                "total_price": f.total_price,
                "currency": f.currency,
                "cabin_class": f.cabin_class,
                "segments": [
                    {
                        "flight_number": s.flight_number,
                        "airline": s.airline,
                        "origin": s.origin,
                        "destination": s.destination,
                        "departure_time": s.departure_time,
                        "arrival_time": s.arrival_time,
                        "duration": s.duration
                    }
                    for s in f.segments
                ]
            }
            for f in result.flights
        ]

        logger.info(f"Source {source} returned {len(flights)} flights")

        return {
            "success": True,
            "source": source,
            "search_id": result.search_id,
            "flights": flights,
            "total_results": result.total_results
        }

    except Exception as e:
        logger.warning(f"Source {source} failed: {e}")
        return {
            "success": False,
            "source": source,
            "error": str(e),
            "flights": []
        }
    finally:
        await client.close()


async def search_all_sources(params: dict) -> dict:
    """Execute flight search across all sources in parallel."""
    logger.info(f"Searching all sources: {API_SOURCES}")

    # Run searches in parallel
    tasks = [search_single_source(source, params) for source in API_SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results
    all_flights = []
    successful_sources = []
    failed_sources = []

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Search task exception: {result}")
            continue

        if result.get("success"):
            all_flights.extend(result.get("flights", []))
            successful_sources.append(result["source"])
        else:
            failed_sources.append(result["source"])

    # Sort by price (lowest first)
    all_flights.sort(key=lambda x: x.get("total_price", float("inf")))

    logger.info(
        f"Search completed: {len(all_flights)} flights from {successful_sources}, "
        f"failed sources: {failed_sources}"
    )

    return {
        "success": len(all_flights) > 0,
        "flights": all_flights,
        "total_results": len(all_flights),
        "has_more": len(all_flights) > 10,
        "sources": {
            "successful": successful_sources,
            "failed": failed_sources
        }
    }


def format_flight_results(search_result: dict, params: dict) -> str:
    """Format flight results for display."""
    if not search_result.get("success"):
        return "❌ Không thể tìm kiếm chuyến bay. Vui lòng thử lại sau."

    flights = search_result.get("flights", [])
    total = search_result.get("total_results", 0)
    sources = search_result.get("sources", {})

    if not flights:
        return "😔 Không tìm thấy chuyến bay phù hợp. Vui lòng thử ngày khác hoặc điều chỉnh tiêu chí tìm kiếm."

    origin = params.get("origin", "")
    destination = params.get("destination", "")
    date = params.get("departure_date", "")

    # Header
    lines = [
        f"🔍 **Tìm thấy {total} chuyến bay {origin} → {destination}** (ngày {date})",
        f"📡 Nguồn: {', '.join(sources.get('successful', []))}",
        "",
        "📋 **Top 10 giá tốt nhất:**",
        ""
    ]

    # Display top 10 flights
    for i, flight in enumerate(flights[:10], 1):
        segments = flight.get("segments", [])
        if not segments:
            continue

        first_seg = segments[0]
        price = flight.get("total_price", 0)
        price_formatted = f"{price:,.0f}".replace(",", ".")
        source = flight.get("source", "?")

        # Flight info
        airline = first_seg.get("airline", "")
        flight_num = first_seg.get("flight_number", "")
        dep_time = first_seg.get("departure_time", "")
        arr_time = segments[-1].get("arrival_time", "")

        # Multi-segment display
        if len(segments) > 1:
            stops = len(segments) - 1
            lines.append(f"**{i}.** {airline} {flight_num} ({stops} điểm dừng) `[{source}]`")
        else:
            lines.append(f"**{i}.** {airline} {flight_num} `[{source}]`")

        lines.append(f"   🕐 {dep_time} → {arr_time}")
        lines.append(f"   💰 **{price_formatted} VND**")
        lines.append("")

    # Footer
    if search_result.get("has_more"):
        remaining = total - 10
        lines.append(f"💡 *Còn {remaining} chuyến bay khác. Bạn muốn xem thêm không?*")

    failed = sources.get("failed", [])
    if failed:
        lines.append(f"\n⚠️ *Không lấy được dữ liệu từ: {', '.join(failed)}*")

    return "\n".join(lines)


async def flight_agent_node(state: AgentState) -> dict:
    """
    Flight agent for searching and comparing flights across multiple sources.
    """
    logger.info("Flight agent processing request")

    # Get search params from state
    params = state.flight_search.model_dump() if state.flight_search else {}
    search_type = params.get("search_type", "oneway")

    # Check capability availability first
    capability_id = f"flight_search_{search_type}"
    if not is_capability_available(capability_id):
        logger.info(f"Capability {capability_id} not available")
        response = get_not_supported_message(capability_id)
        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "flight"
        }

    # Check for country suggestions first
    country_suggestions = params.get("country_suggestions", [])
    if country_suggestions:
        # Build suggestion message
        lines = ["✈️ Bạn muốn bay đến đâu? Đây là các sân bay phổ biến:\n"]
        for suggestion in country_suggestions:
            country = suggestion.get("country", "").title()
            airports = suggestion.get("airports", [])
            lines.append(f"**{country}:**")
            for airport in airports:
                lines.append(f"  • {airport}")
            lines.append("")

        lines.append("💡 *Vui lòng cho tôi biết thành phố hoặc mã sân bay cụ thể (VD: ICN, NRT, BKK)*")

        response = "\n".join(lines)
        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "flight"
        }

    # Check required parameters
    missing_params = []
    if not params.get("origin"):
        missing_params.append("điểm đi (VD: SGN, HAN, DAD)")
    if not params.get("destination"):
        missing_params.append("điểm đến")
    if not params.get("departure_date"):
        missing_params.append("ngày đi (VD: 25/12/2025)")

    if missing_params:
        missing_str = ", ".join(missing_params)
        response = (
            f"✈️ Để tìm chuyến bay, tôi cần thêm thông tin:\n"
            f"• {missing_str}\n\n"
            f"**Ví dụ:** Tìm vé từ SGN đến HAN ngày 25/12/2025, 1 người"
        )
        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "flight"
        }

    # Execute search across all sources
    logger.info(
        "Executing multi-source flight search",
        origin=params.get("origin"),
        destination=params.get("destination"),
        date=params.get("departure_date")
    )

    search_result = await search_all_sources(params)

    # Format results
    response = format_flight_results(search_result, params)

    # Update state
    flight_results = FlightSearchResult(
        search_id=f"multi_{params.get('origin')}_{params.get('destination')}",
        flights=search_result.get("flights", [])[:20],  # Keep top 20
        total_results=search_result.get("total_results", 0),
        has_more=search_result.get("has_more", False)
    )

    return {
        "messages": [AIMessage(content=response)],
        "flight_results": flight_results,
        "current_agent": "flight"
    }
