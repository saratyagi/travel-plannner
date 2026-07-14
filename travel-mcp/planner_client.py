import json
import httpx


async def call_plan(message: str, api_url: str) -> str:
    """Stream POST /api/plan and return the final report text."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{api_url}/api/plan",
            json={"message": message},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                t = event.get("type")
                if t == "complete":
                    return event["report"]
                if t == "error":
                    raise RuntimeError(event.get("message", "Planner returned an error."))
                if t == "clarification":
                    raise RuntimeError(
                        f"Planner needs more information: {event.get('message', '')} "
                        "Make sure destination, start_date, end_date, and travelers are provided."
                    )
    raise RuntimeError("Planner closed the stream without returning a complete plan.")
