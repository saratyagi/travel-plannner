import json

from agents.base import run_agent
from models.schemas import TripRequest

FLIGHT_SYSTEM = """You are a flight search specialist. Use web_search to find real, current flight options.

Search strategy:
1. Search for the cheapest available flights (budget airlines, connections allowed)
2. Search for balanced options (reasonable price + convenient routing)
3. Search for premium options (premium economy or business class)

Perform multiple searches to gather enough data. Use queries like:
- "cheapest flights [origin] to [destination] [date]"
- "[airline] [route] price [date]"

Return ONLY a valid JSON array — no prose, no markdown fences, no extra text:
[
  {
    "label": "cheapest",
    "airline": "Airline Name",
    "route_summary": "JFK → CDG (nonstop)" or "JFK → LHR → CDG (1 stop)",
    "layovers": 0,
    "duration": "7h 30m",
    "price_estimate_usd": 450,
    "source_note": "Brief source attribution"
  }
]

Return exactly 3–5 FlightOption objects covering cheapest / balanced / premium spread."""

FALLBACK_FLIGHTS = [
    {
        "label": "cheapest",
        "airline": "Budget Carrier",
        "route_summary": "Connecting route",
        "layovers": 1,
        "duration": "Varies",
        "price_estimate_usd": 350,
        "source_note": "Estimated — live data unavailable",
    },
    {
        "label": "balanced",
        "airline": "Major Airline",
        "route_summary": "Direct or 1 stop",
        "layovers": 1,
        "duration": "Varies",
        "price_estimate_usd": 650,
        "source_note": "Estimated — live data unavailable",
    },
    {
        "label": "premium",
        "airline": "Premium Airline",
        "route_summary": "Business class route",
        "layovers": 0,
        "duration": "Varies",
        "price_estimate_usd": 1800,
        "source_note": "Estimated — live data unavailable",
    },
]


async def search_flights(trip: TripRequest) -> list:
    date_info = (
        f"Departure: {trip.start_date}, Return: {trip.end_date}"
        if trip.start_date and trip.end_date
        else f"Approximate duration: {trip.trip_length_days} days (exact dates flexible)"
    )
    prompt = (
        f"Find flights for this trip:\n"
        f"- From: {trip.origin}\n"
        f"- To: {trip.destination}\n"
        f"- {date_info}\n"
        f"- Travelers: {trip.travelers}\n"
        f"- Cabin class: {trip.cabin_class}\n\n"
        f"Search for cheapest, balanced, and premium options. "
        f"If dates are approximate, search for typical prices for that season. "
        f"Note approximate dates in source_note if used. "
        f"Return a JSON array of FlightOption objects."
    )

    raw = await run_agent(FLIGHT_SYSTEM, prompt, use_tools=True, max_tokens=4096, fast=False, max_tool_iterations=2, agent_name="flight")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw.strip())
        return data if isinstance(data, list) and data else FALLBACK_FLIGHTS
    except Exception:
        return FALLBACK_FLIGHTS
