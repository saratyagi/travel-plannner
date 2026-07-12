import asyncio
import os
from typing import Any

from adapters.llm import AnthropicAdapter
from tools.web_tools import execute_web_search, execute_web_fetch

ANTHROPIC_API_KEY = os.environ.get("travel_planner")
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "").lower() in ("1", "true", "yes")

_llm_adapter = AnthropicAdapter(api_key=ANTHROPIC_API_KEY)

# Fast model for pure-reasoning agents (budget, report, etc.)
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

_MOCK_DELAYS: dict[str, float] = {
    "flight":       1.4,
    "hotel":        1.4,
    "report":       1.0,
    "budget":       0.7,
    "attractions":  0.6,
    "extract":      0.3,
    "clarify_hard": 0.2,
    "clarify_soft": 0.2,
}


async def _execute_tool(name: str, inputs: dict[str, Any]) -> str:
    if name == "web_search":
        return await execute_web_search(inputs["query"])
    if name == "web_fetch":
        return await execute_web_fetch(inputs["url"])
    return f"Unknown tool: {name}"


def _mock_run_agent(agent_name: str, user_message: str) -> str:
    from fixtures.mock_data import (
        get_mock_trip_params, get_mock_flights_json, get_mock_hotels_json,
        get_mock_budget_json, get_mock_report, get_mock_attractions_json,
        MOCK_HARD_QUESTION, MOCK_SOFT_QUESTION,
    )
    dispatch = {
        "extract":      lambda: get_mock_trip_params(user_message),
        "flight":       lambda: get_mock_flights_json(user_message),
        "hotel":        lambda: get_mock_hotels_json(user_message),
        "budget":       lambda: get_mock_budget_json(user_message),
        "report":       lambda: get_mock_report(user_message),
        "attractions":  lambda: get_mock_attractions_json(user_message),
        "clarify_hard": lambda: MOCK_HARD_QUESTION,
        "clarify_soft": lambda: MOCK_SOFT_QUESTION,
    }
    handler = dispatch.get(agent_name)
    return handler() if handler else ""


async def run_agent(
    system_prompt: str,
    user_message: str,
    use_tools: bool = False,
    max_tokens: int = 4096,
    fast: bool = False,
    max_tool_iterations: int = 3,
    agent_name: str = "",
) -> str:
    if USE_MOCK_DATA:
        delay = _MOCK_DELAYS.get(agent_name, 0.0)
        if delay:
            await asyncio.sleep(delay)
        return _mock_run_agent(agent_name, user_message)

    messages: list[dict] = [{"role": "user", "content": user_message}]
    tools = SEARCH_TOOLS if use_tools else []
    model = FAST_MODEL if fast else SEARCH_MODEL
    iterations = 0

    while True:
        response = await _llm_adapter.complete(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=max_tokens,
            tools=tools,
        )

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
