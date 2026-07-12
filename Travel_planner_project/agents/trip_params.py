import json
from datetime import datetime, timedelta

from agents.base import run_agent

# ── Extraction prompt ────────────────────────────────────────────────────────

EXTRACT_SYSTEM = """You are a travel planning assistant. Extract trip parameters from the user's message (which may include conversation history).

Return ONLY a valid JSON object — no prose, no markdown fences:
{
  "origin": "city or airport code, or null",
  "destination": "city or airport code, or null",
  "start_date": "YYYY-MM-DD or null",
  "end_date": "YYYY-MM-DD or null",
  "trip_length_days": integer or null,
  "travelers": integer or null,
  "cabin_class": "economy",
  "hotel_pref": "any",
  "budget_ceiling_usd": number or null
}

Rules:
- cabin_class: economy | premium_economy | business | first  (default: economy)
- hotel_pref: budget | mid | luxury | any  (default: any)
- Current year is 2026. Resolve relative dates ("next month", "in October") to actual dates.
- If the user says "7 days in October", set trip_length_days=7 and start_date to a reasonable October date.
- If exact dates given, fill start_date + end_date AND set trip_length_days from the difference.
- If travelers not mentioned, return null (do not default to 1).
- budget_ceiling_usd: only set if user explicitly states a budget limit."""

# ── Clarification question prompts ───────────────────────────────────────────

HARD_QUESTION_SYSTEM = """You are a friendly travel assistant. The user wants to plan a trip but key details are missing.
Ask ONE natural, concise question to get the missing information. Do NOT list what you already know — just ask what's missing.
Keep it to 1-2 sentences."""

SOFT_QUESTION_SYSTEM = """You are a friendly travel assistant helping plan a trip.
You have the destination, origin, and dates. Now ask about remaining optional details in a single friendly message.
Always offer a way to skip ("or I can assume solo travel and show the full price range").
Keep it to 2-3 sentences max."""


# ── Deterministic validator ──────────────────────────────────────────────────

def validate_fields(params: dict) -> tuple[list[str], list[str]]:
    """Returns (hard_missing, soft_missing). Pure logic — no LLM."""
    hard, soft = [], []

    if not params.get("origin"):
        hard.append("origin")
    if not params.get("destination"):
        hard.append("destination")

    has_dates = params.get("start_date") and params.get("end_date")
    has_length = params.get("trip_length_days")
    if not has_dates and not has_length:
        hard.append("dates")

    if params.get("travelers") is None:
        soft.append("travelers")

    return hard, soft


def apply_defaults(params: dict) -> tuple[dict, list[str]]:
    """Apply soft-field defaults and return list of assumptions made."""
    assumptions = []
    if params.get("travelers") is None:
        params["travelers"] = 1
        assumptions.append("Solo traveler assumed")
    if params.get("budget_ceiling_usd") is None:
        assumptions.append("No fixed budget ceiling — showing full low/mid/high range")
    return params, assumptions


def resolve_dates(params: dict) -> dict:
    """If only trip_length_days given, derive start/end dates (use next suitable month)."""
    if params.get("start_date") and params.get("end_date"):
        return params
    if params.get("trip_length_days") and not params.get("start_date"):
        # Default: start 30 days from today
        start = datetime.now() + timedelta(days=30)
        end = start + timedelta(days=params["trip_length_days"])
        params["start_date"] = start.strftime("%Y-%m-%d")
        params["end_date"] = end.strftime("%Y-%m-%d")
    elif params.get("start_date") and params.get("trip_length_days") and not params.get("end_date"):
        start = datetime.strptime(params["start_date"], "%Y-%m-%d")
        end = start + timedelta(days=params["trip_length_days"])
        params["end_date"] = end.strftime("%Y-%m-%d")
    return params


# ── LLM helpers ──────────────────────────────────────────────────────────────

async def extract_trip_params(message: str, partial: dict | None = None) -> dict:
    raw = await run_agent(EXTRACT_SYSTEM, message, use_tools=False, max_tokens=512, fast=True, agent_name="extract")
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        extracted = json.loads(raw)
    except Exception:
        extracted = {}

    if partial:
        # Merge: keep existing values, overwrite only if new extraction has a non-null value
        merged = dict(partial)
        for k, v in extracted.items():
            if v is not None and v != "null":
                merged[k] = v
        return merged

    return extracted


async def ask_hard_question(params: dict, missing: list[str]) -> str:
    context = []
    if params.get("destination"):
        context.append(f"destination: {params['destination']}")
    if params.get("origin"):
        context.append(f"from: {params['origin']}")
    ctx_str = f"Known so far: {', '.join(context)}. " if context else ""
    prompt = f"{ctx_str}Missing: {', '.join(missing)}. Ask a natural follow-up question."
    return await run_agent(HARD_QUESTION_SYSTEM, prompt, use_tools=False, max_tokens=128, fast=True, agent_name="clarify_hard")


async def ask_soft_question(params: dict, missing: list[str]) -> str:
    known = (
        f"Trip: {params.get('origin')} → {params.get('destination')}, "
        f"{params.get('start_date', '')} to {params.get('end_date', '')} "
        f"({params.get('trip_length_days', '?')} days)."
    )
    prompt = f"{known} Still missing (soft): {', '.join(missing)}. Ask a combined friendly question with a skip option."
    return await run_agent(SOFT_QUESTION_SYSTEM, prompt, use_tools=False, max_tokens=128, fast=True, agent_name="clarify_soft")
