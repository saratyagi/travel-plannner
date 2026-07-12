import json
from datetime import datetime

from agents.base import run_agent
from models.schemas import TripRequest

BUDGET_SYSTEM = """You are a travel budget analyst. Calculate realistic cost estimates from flight and hotel data.

Return ONLY a valid JSON BudgetEstimate object — no prose, no markdown fences:
{
  "flights_usd":          {"low": 0, "mid": 0, "high": 0},
  "hotel_usd":            {"low": 0, "mid": 0, "high": 0},
  "food_usd":             {"low": 0, "mid": 0, "high": 0},
  "local_transport_usd":  {"low": 0, "mid": 0, "high": 0},
  "activities_usd":       {"low": 0, "mid": 0, "high": 0},
  "buffer_usd":           {"low": 0, "mid": 0, "high": 0},
  "total_usd":            {"low": 0, "mid": 0, "high": 0},
  "uncertain_categories": []
}

Calculation rules:
- flights: low = cheapest option × travelers, mid = average, high = premium option × travelers
- hotel: low = budget nightly × nights, mid = mid_range nightly × nights, high = luxury nightly × nights
- food: $25–50 / person / day (low), $60–100 (mid), $120–250 (high); multiply by travelers × nights
- local_transport: $10–20 / day (low), $25–40 (mid), $50–80 (high); multiply by travelers × nights
- activities: $20–40 / day (low), $50–80 (mid), $100–200 (high); multiply by travelers × nights
- buffer: exactly 10 % of (flights + hotel + food + transport + activities) for each tier
- total: sum of all 5 categories + buffer for each tier
- Add category name to uncertain_categories if the underlying data is estimated or unreliable"""

FALLBACK_BUDGET = {
    "flights_usd": {"low": 300, "mid": 700, "high": 1500},
    "hotel_usd": {"low": 560, "mid": 1050, "high": 2800},
    "food_usd": {"low": 350, "mid": 700, "high": 1750},
    "local_transport_usd": {"low": 140, "mid": 280, "high": 560},
    "activities_usd": {"low": 280, "mid": 560, "high": 1400},
    "buffer_usd": {"low": 163, "mid": 329, "high": 801},
    "total_usd": {"low": 1793, "mid": 3619, "high": 8811},
    "uncertain_categories": ["all — fallback estimates used"],
}


async def calculate_budget(trip: TripRequest, flights: list, hotels: list) -> dict:
    try:
        nights = (
            datetime.strptime(trip.end_date, "%Y-%m-%d")
            - datetime.strptime(trip.start_date, "%Y-%m-%d")
        ).days
    except Exception:
        nights = 7

    prompt = (
        f"Calculate the budget estimate for this trip:\n\n"
        f"Trip: {trip.origin} → {trip.destination}\n"
        f"Duration: {nights} nights | Travelers: {trip.travelers}\n\n"
        f"Flight options:\n{json.dumps(flights, indent=2)}\n\n"
        f"Hotel options:\n{json.dumps(hotels, indent=2)}\n\n"
        f"Produce a detailed BudgetEstimate JSON."
    )

    raw = await run_agent(BUDGET_SYSTEM, prompt, use_tools=False, max_tokens=2048, fast=True, agent_name="budget")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw.strip())
    except Exception:
        return FALLBACK_BUDGET
