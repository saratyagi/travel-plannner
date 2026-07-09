import json
from datetime import datetime

from agents.base import run_agent
from models.schemas import TripRequest

HOTEL_SYSTEM = """You are a hotel search specialist. Use web_search to find real hotel options at the destination.

Search for hotels across three tiers:
1. Budget (hostels, 2–3 star, guesthouses)
2. Mid-range (3–4 star, good amenities)
3. Luxury (5 star, premium experience)

Use queries like:
- "budget hotels [destination] price per night [dates]"
- "best mid-range hotels [destination] [year]"
- "luxury hotels [destination] nightly rate"

Return ONLY a valid JSON array — no prose, no markdown fences, no extra text:
[
  {
    "label": "budget",
    "name": "Hotel Name",
    "area": "Neighborhood or district",
    "nightly_rate_usd": 80,
    "amenities": ["WiFi", "Breakfast"],
    "source_note": "Brief source attribution"
  }
]

Return exactly 3–5 HotelOption objects spanning budget / mid_range / luxury."""

FALLBACK_HOTELS = [
    {
        "label": "budget",
        "name": "Local Budget Hotel",
        "area": "City Center",
        "nightly_rate_usd": 70,
        "amenities": ["WiFi", "24h Reception"],
        "source_note": "Estimated — live data unavailable",
    },
    {
        "label": "mid_range",
        "name": "Comfort Inn",
        "area": "Downtown",
        "nightly_rate_usd": 150,
        "amenities": ["WiFi", "Breakfast", "Gym"],
        "source_note": "Estimated — live data unavailable",
    },
    {
        "label": "luxury",
        "name": "Grand Hotel",
        "area": "Premium District",
        "nightly_rate_usd": 400,
        "amenities": ["WiFi", "Spa", "Pool", "Restaurant"],
        "source_note": "Estimated — live data unavailable",
    },
]


async def search_hotels(trip: TripRequest) -> list:
    try:
        nights = (
            datetime.strptime(trip.end_date, "%Y-%m-%d")
            - datetime.strptime(trip.start_date, "%Y-%m-%d")
        ).days
    except Exception:
        nights = trip.trip_length_days or 7

    date_info = (
        f"Check-in: {trip.start_date}, Check-out: {trip.end_date}"
        if trip.start_date and trip.end_date
        else f"Approximate stay: {nights} nights (exact dates flexible)"
    )
    prompt = (
        f"Find hotels for this trip:\n"
        f"- Destination: {trip.destination}\n"
        f"- {date_info} ({nights} nights)\n"
        f"- Travelers: {trip.travelers}\n"
        f"- Preference: {trip.hotel_pref}\n\n"
        f"Search across budget, mid-range, and luxury tiers. "
        f"Note approximate dates in source_note if used. "
        f"Return a JSON array of HotelOption objects."
    )

    raw = await run_agent(HOTEL_SYSTEM, prompt, use_tools=True, max_tokens=4096, fast=False, max_tool_iterations=2)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw.strip())
        return data if isinstance(data, list) and data else FALLBACK_HOTELS
    except Exception:
        return FALLBACK_HOTELS
