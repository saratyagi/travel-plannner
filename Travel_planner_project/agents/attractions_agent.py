import asyncio
import json
import os

import httpx

from agents.base import run_agent, USE_MOCK_DATA
from tools.web_tools import execute_web_search

_image_cache: dict[str, str | None] = {}

EXTRACT_SYSTEM = """You are a travel expert. Given search results about a destination, extract the top 5 must-see attractions.

Return ONLY a valid JSON array — no prose, no markdown fences:
[
  {
    "name": "Attraction Name",
    "category": "Temple/Museum/Park/Beach/Market/Palace/etc",
    "description": "One vivid sentence about why this place is special.",
    "estimated_cost_usd": 0,
    "cost_note": "Free entry"
  }
]

Rules:
- estimated_cost_usd: 0 for free, otherwise typical entry fee per adult in USD
- cost_note: human-readable string like "Free entry", "$15 per person", "₹600 (~$7)"
- Include a mix of free and paid options
- Return exactly 5 attractions"""


async def _image_search(query: str) -> str | None:
    if USE_MOCK_DATA:
        from tools.mock_data import get_mock_image_url
        return get_mock_image_url(query)
    if query in _image_cache:
        return _image_cache[query]
    api_key = os.environ.get("Serper_Api_Key", "")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://google.serper.dev/images",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query, "num": 5},
            )
            resp.raise_for_status()
            images = resp.json().get("images", [])
            result = None
            for img in images:
                url = img.get("imageUrl", "")
                if url and url.startswith("http") and not url.endswith(".svg"):
                    result = url
                    break
            _image_cache[query] = result
            return result
    except Exception:
        _image_cache[query] = None
        return None


async def search_attractions(destination: str) -> list:
    if not destination:
        return []

    results = await execute_web_search(
        f"top tourist attractions {destination} entry fee visitor cost 2026"
    )

    raw = await run_agent(
        EXTRACT_SYSTEM,
        f"Destination: {destination}\n\nSearch results:\n{results}",
        use_tools=False,
        max_tokens=1024,
        fast=True,
    )
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        places = json.loads(raw)
        if not isinstance(places, list):
            return []
    except Exception:
        return []

    places = places[:5]

    # Fetch one image per attraction in parallel
    image_tasks = [
        _image_search(f"{p.get('name', '')} {destination} landmark")
        for p in places
    ]
    images = await asyncio.gather(*image_tasks, return_exceptions=True)

    for i, place in enumerate(places):
        img = images[i] if i < len(images) and not isinstance(images[i], Exception) else None
        place["image_url"] = img

    return places
