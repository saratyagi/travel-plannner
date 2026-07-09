import asyncio
from typing import AsyncGenerator, Optional

from models.schemas import TripRequest
from agents.attractions_agent import search_attractions
from agents.orchestrator import (
    extract_trip_params, validate_fields, apply_defaults,
    resolve_dates, ask_hard_question, ask_soft_question,
)
from agents.flight_agent import search_flights
from agents.hotel_agent import search_hotels
from agents.budget_agent import calculate_budget
from agents.report_generator import generate_report
from tools.currency import get_usd_to_inr


class TravelPlanner:
    async def run(
        self,
        user_message: str,
        partial_params: Optional[dict] = None,
        conversation_history: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:

        # ── Step 1: Extract params ──────────────────────────────────────────
        yield {"type": "progress", "agent": "orchestrator", "status": "running",
               "message": "Analyzing your trip request…"}

        # Build the full message context for the LLM
        full_message = user_message
        if conversation_history:
            full_message = f"{conversation_history}\nUser's latest reply: {user_message}"

        try:
            params = await extract_trip_params(full_message, partial=partial_params)
        except Exception as exc:
            yield {"type": "error", "message": f"Could not parse trip request: {exc}"}
            return

        # ── Step 2: Validate ────────────────────────────────────────────────
        hard_missing, soft_missing = validate_fields(params)

        # Hard-blocking fields missing → ask and stop
        if hard_missing:
            question = await ask_hard_question(params, hard_missing)
            yield {
                "type": "clarification",
                "clarification_type": "hard",
                "message": question,
                "missing_fields": hard_missing,
                "partial_params": params,
                "conversation_history": (
                    f"{conversation_history}\nUser: {user_message}\nAssistant: {question}"
                    if conversation_history
                    else f"User: {user_message}\nAssistant: {question}"
                ),
            }
            return

        # Soft-blocking fields missing → ask once, then proceed with defaults
        if soft_missing:
            question = await ask_soft_question(params, soft_missing)
            yield {
                "type": "clarification",
                "clarification_type": "soft",
                "message": question,
                "missing_fields": soft_missing,
                "partial_params": params,
                "conversation_history": (
                    f"{conversation_history}\nUser: {user_message}\nAssistant: {question}"
                    if conversation_history
                    else f"User: {user_message}\nAssistant: {question}"
                ),
            }
            return

        # ── Step 3: Apply defaults + resolve dates ──────────────────────────
        params, assumptions = apply_defaults(params)
        params = resolve_dates(params)

        try:
            trip = TripRequest(
                origin=params.get("origin", "Unknown"),
                destination=params["destination"],
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                trip_length_days=params.get("trip_length_days"),
                travelers=int(params.get("travelers", 1)),
                cabin_class=params.get("cabin_class", "economy"),
                hotel_pref=params.get("hotel_pref", "any"),
                budget_ceiling_usd=params.get("budget_ceiling_usd"),
                assumptions=assumptions,
            )
        except Exception as exc:
            yield {"type": "error", "message": f"Invalid trip parameters: {exc}"}
            return

        yield {"type": "progress", "agent": "orchestrator", "status": "done",
               "message": f"Planning: {trip.origin} → {trip.destination}"}
        yield {"type": "trip_params", "data": trip.dict()}

        # ── Step 4: Flight + Hotel in parallel ─────────────────────────────
        yield {"type": "progress", "agent": "flight", "status": "running",
               "message": "Searching for flights…"}
        yield {"type": "progress", "agent": "hotel", "status": "running",
               "message": "Searching for hotels…"}

        flights_result, hotels_result = await asyncio.gather(
            search_flights(trip),
            search_hotels(trip),
            return_exceptions=True,
        )

        flights = flights_result if not isinstance(flights_result, Exception) else []
        hotels = hotels_result if not isinstance(hotels_result, Exception) else []

        yield {"type": "progress", "agent": "flight", "status": "done",
               "message": f"Found {len(flights)} flight option(s)"}
        yield {"type": "progress", "agent": "hotel", "status": "done",
               "message": f"Found {len(hotels)} hotel option(s)"}

        # ── Step 5: Budget ──────────────────────────────────────────────────
        yield {"type": "progress", "agent": "budget", "status": "running",
               "message": "Calculating budget estimates…"}

        try:
            budget = await calculate_budget(trip, flights, hotels)
        except Exception as exc:
            yield {"type": "error", "message": f"Budget calculation failed: {exc}"}
            return

        yield {"type": "progress", "agent": "budget", "status": "done",
               "message": "Budget estimate ready"}

        # ── Step 6: Report + Attractions in parallel ────────────────────────
        yield {"type": "progress", "agent": "report", "status": "running",
               "message": "Generating your travel plan…"}

        inr_rate = await get_usd_to_inr()

        report_result, attractions_result = await asyncio.gather(
            generate_report(trip, flights, hotels, budget, inr_rate),
            search_attractions(trip.destination or ""),
            return_exceptions=True,
        )

        if isinstance(report_result, Exception):
            yield {"type": "error", "message": f"Report generation failed: {report_result}"}
            return

        yield {"type": "progress", "agent": "report", "status": "done",
               "message": "Travel plan complete!"}
        yield {"type": "complete", "report": report_result}

        if not isinstance(attractions_result, Exception) and attractions_result:
            yield {"type": "attractions", "places": attractions_result}
