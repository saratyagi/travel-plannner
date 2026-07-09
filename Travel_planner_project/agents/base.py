import asyncio
import os
from typing import Any

import anthropic

from tools.web_tools import execute_web_search, execute_web_fetch

ANTHROPIC_API_KEY = os.environ.get("travel_planner")
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "").lower() in ("1", "true", "yes")

# Fast model for pure-reasoning agents (orchestrator, budget, report)
FAST_MODEL = "claude-haiku-4-5-20251001"
# Search model for agents that use web tools (flight, hotel)
SEARCH_MODEL = "claude-sonnet-4-6"

SEARCH_TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current, real-time information about flights, hotels, "
            "and travel. Use specific, targeted queries to get accurate prices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_fetch",
        "description": "Fetch the full content of a URL to retrieve detailed travel information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"}
            },
            "required": ["url"],
        },
    },
]


async def _execute_tool(name: str, inputs: dict[str, Any]) -> str:
    if name == "web_search":
        return await execute_web_search(inputs["query"])
    if name == "web_fetch":
        return await execute_web_fetch(inputs["url"])
    return f"Unknown tool: {name}"


def _mock_run_agent(system_prompt: str, user_message: str) -> str:
    from tools.mock_data import (
        get_mock_trip_params, get_mock_flights_json, get_mock_hotels_json,
        get_mock_budget_json, get_mock_report, get_mock_attractions_json,
        MOCK_HARD_QUESTION, MOCK_SOFT_QUESTION,
    )
    sp = system_prompt.lower()
    if "extract trip parameters" in sp:
        return get_mock_trip_params(user_message)
    if "flight search specialist" in sp:
        return get_mock_flights_json(user_message)
    if "hotel search specialist" in sp:
        return get_mock_hotels_json(user_message)
    if "budget analyst" in sp:
        return get_mock_budget_json(user_message)
    if "travel writing expert" in sp:
        return get_mock_report(user_message)
    if "must-see attractions" in sp:
        return get_mock_attractions_json(user_message)
    if "key details are missing" in sp:
        return MOCK_HARD_QUESTION
    if "optional details" in sp:
        return MOCK_SOFT_QUESTION
    return ""


async def run_agent(
    system_prompt: str,
    user_message: str,
    use_tools: bool = False,
    max_tokens: int = 4096,
    fast: bool = False,
    max_tool_iterations: int = 3,
) -> str:
    if USE_MOCK_DATA:
        sp_lower = system_prompt.lower()
        # Stagger delays so each planning step is visible in the UI animations
        if "flight search specialist" in sp_lower or "hotel search specialist" in sp_lower:
            await asyncio.sleep(1.4)
        elif "travel writing expert" in sp_lower:
            await asyncio.sleep(1.0)
        elif "budget analyst" in sp_lower:
            await asyncio.sleep(0.7)
        elif "must-see attractions" in sp_lower:
            await asyncio.sleep(0.6)
        elif "extract trip parameters" in sp_lower:
            await asyncio.sleep(0.3)
        elif "key details are missing" in sp_lower or "optional details" in sp_lower:
            await asyncio.sleep(0.2)
        return _mock_run_agent(system_prompt, user_message)
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    messages: list[dict] = [{"role": "user", "content": user_message}]
    tools = SEARCH_TOOLS if use_tools else []
    model = FAST_MODEL if fast else SEARCH_MODEL
    iterations = 0

    while True:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.messages.create(**kwargs)

        if response.stop_reason == "tool_use" and iterations < max_tool_iterations:
            iterations += 1
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await _execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""
