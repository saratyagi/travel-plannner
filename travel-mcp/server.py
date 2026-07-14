"""
Travel Planner MCP Server — v0.5
Exposes travel planning and trip storage as MCP tools.
Run with --http to serve via streamable-HTTP (for Claude Connectors).
Run without args for stdio transport (for Claude Code / desktop config).
"""
import json
import re
import sys
import uuid

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from planner_client import call_plan
from storage import (
    init_db, get_all_trips, load_trip,
    store_trip, get_activities,
    add_activity_row, update_activity_row, remove_activity_row,
)

BACKEND_URL = "http://localhost:8001"

mcp = FastMCP(
    "travel-planner",
    port=8002,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

_INJECTION_RE = re.compile(
    r"(ignore\s+previous|system\s*:|\[INST\]|<\|im_start\|>)",
    re.IGNORECASE,
)


def _sanitize(text: str) -> str:
    return _INJECTION_RE.sub("[filtered]", text)


# ─── Planning tool ───────────────────────────────────────────────────────────

@mcp.tool()
async def plan_trip(request: str) -> str:
    """Research and generate a complete travel plan using AI agents.

    Searches for real flights, hotels, and calculates a full budget breakdown.
    Always include origin city, destination, travel dates, number of travelers,
    and any preferences (budget range, cabin class, hotel type) in your request.

    Example: "Fly from Delhi to Paris, Aug 10-17 2026, 2 travelers, economy, mid-range budget"

    Returns a complete travel plan with flight options, hotel options, and budget estimates.
    """
    try:
        report = await call_plan(request, BACKEND_URL)
        return report
    except RuntimeError as exc:
        return f"Planning error: {exc}"
    except Exception as exc:
        return f"Could not connect to travel planner backend ({BACKEND_URL}). Make sure it is running. Error: {exc}"


# ─── Read tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def list_trips() -> str:
    """List all saved trips with their IDs.

    Always call this first to discover valid trip IDs before calling
    get_trip, add_activity, update_activity, or remove_activity.
    """
    await init_db()
    trips = await get_all_trips()
    if not trips:
        return "No trips saved yet. Call save_trip to store a plan."
    lines = ["Saved trips:\n"]
    for t in trips:
        lines.append(
            f"• ID: {t['id']}\n"
            f"  Destination: {_sanitize(t['destination'])}\n"
            f"  Origin: {_sanitize(t.get('origin', ''))}\n"
            f"  Dates: {t['start_date']} → {t['end_date']}\n"
            f"  Travelers: {t['travelers']}\n"
            f"  Saved: {t['created_at'][:10]}\n"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_trip(trip_id: str) -> str:
    """Retrieve the full itinerary for a saved trip.

    Do not guess trip IDs — call list_trips first.
    """
    await init_db()
    trip = await load_trip(trip_id)
    if not trip:
        return f"No trip found with ID '{trip_id}'. Call list_trips to see valid IDs."

    activities = await get_activities(trip_id)
    parts = [
        f"=== {_sanitize(trip['destination'])} ===",
        f"Origin:    {_sanitize(trip.get('origin', ''))}",
        f"Dates:     {trip['start_date']} to {trip['end_date']}",
        f"Travelers: {trip['travelers']}",
        "",
        _sanitize(trip["plan_text"]),
    ]

    if activities:
        parts.append("\n--- Custom Activities ---")
        by_day: dict[int, list] = {}
        for a in activities:
            by_day.setdefault(a["day"], []).append(a)
        for day in sorted(by_day):
            parts.append(f"\nDay {day}:")
            for a in by_day[day]:
                time_part = f" at {a['time']}" if a.get("time") else ""
                notes_part = f" — {a['notes']}" if a.get("notes") else ""
                parts.append(
                    f"  • {_sanitize(a['name'])}{time_part}{notes_part}"
                    f"  (activity_id: {a['id']})"
                )

    return "\n".join(parts)


# ─── Write tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def save_trip(
    destination: str,
    origin: str,
    start_date: str,
    end_date: str,
    travelers: int,
    itinerary_json: str,
) -> str:
    """Save a completed trip plan to the travel planner.

    Args:
        destination: Any city, region, or country.
        origin: Departure city or airport.
        start_date: ISO format YYYY-MM-DD.
        end_date: ISO format YYYY-MM-DD.
        travelers: Number of travelers.
        itinerary_json: Day-by-day plan as a JSON string.
            Format: [{"day": 1, "date": "YYYY-MM-DD", "title": "...", "activities": ["...", ...]}, ...]

    Returns the trip_id.
    """
    await init_db()

    try:
        itinerary = json.loads(itinerary_json)
        if not isinstance(itinerary, list):
            return "Invalid itinerary_json: must be a JSON array of day objects."
    except json.JSONDecodeError as exc:
        return f"Invalid itinerary_json: {exc}. Provide a valid JSON string."

    lines = []
    for day in itinerary:
        day_num = day.get("day", "?")
        date = day.get("date", "")
        title = day.get("title", "")
        header = f"Day {day_num}"
        if date:
            header += f" ({date})"
        if title:
            header += f": {title}"
        lines.append(header)
        for act in day.get("activities", []):
            lines.append(f"  • {act}")
        lines.append("")
    plan_text = "\n".join(lines).strip()

    trip_id = str(uuid.uuid4())[:8]
    await store_trip(
        trip_id=trip_id,
        destination=destination,
        origin=origin,
        start_date=start_date,
        end_date=end_date,
        travelers=travelers,
        plan_text=plan_text,
    )

    return (
        f"Trip saved!\n"
        f"Trip ID:     {trip_id}\n"
        f"Destination: {destination}\n"
        f"Origin:      {origin}\n"
        f"Dates:       {start_date} → {end_date}\n"
        f"Travelers:   {travelers}\n\n"
        f"Call get_trip('{trip_id}') to read the plan."
    )


@mcp.tool()
async def add_activity(
    trip_id: str,
    day: int,
    name: str,
    time: str = "",
    notes: str = "",
) -> str:
    """Add a custom activity to an existing trip itinerary.

    Args:
        trip_id: Trip to add the activity to. Use list_trips to find IDs.
        day: Which day of the trip (1-indexed).
        name: Description of the activity.
        time: Optional time of day, e.g. "09:00" or "afternoon".
        notes: Optional extra details or reminders.

    Returns the activity_id.
    """
    await init_db()
    trip = await load_trip(trip_id)
    if not trip:
        return f"No trip found with ID '{trip_id}'. Call list_trips to see valid IDs."

    activity_id = str(uuid.uuid4())[:8]
    await add_activity_row(
        activity_id=activity_id,
        trip_id=trip_id,
        day=day,
        name=name,
        time=time.strip() or None,
        notes=notes.strip() or None,
    )

    time_part = f" at {time.strip()}" if time.strip() else ""
    return (
        f"Activity added to '{trip['destination']}' trip (day {day}): {name}{time_part}\n"
        f"Activity ID: {activity_id}"
    )


@mcp.tool()
async def update_activity(
    activity_id: str,
    name: str = "",
    time: str = "",
    notes: str = "",
) -> str:
    """Edit an existing custom activity in place.

    Only fields you supply are updated — omit a field to leave it unchanged.
    Use get_trip to find activity IDs shown next to each activity.
    """
    await init_db()
    updated = await update_activity_row(
        activity_id=activity_id,
        name=name.strip() or None,
        time=time.strip() or None,
        notes=notes.strip() or None,
    )
    if not updated:
        return (
            f"No activity found with ID '{activity_id}'. "
            "Call get_trip to see valid activity IDs."
        )
    return f"Activity '{activity_id}' updated."


@mcp.tool()
async def remove_activity(activity_id: str) -> str:
    """Remove a custom activity from a trip itinerary.

    Only removes activities added via add_activity.
    Use get_trip to find activity IDs.
    """
    await init_db()
    removed = await remove_activity_row(activity_id)
    if not removed:
        return (
            f"No activity found with ID '{activity_id}'. "
            "Call get_trip to see valid activity IDs."
        )
    return f"Activity '{activity_id}' removed."


if __name__ == "__main__":
    if "--http" in sys.argv:
        # HTTP mode: connect via http://localhost:8002/mcp in Claude Connectors
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
