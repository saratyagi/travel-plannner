import os

from adapters.search import SerperAdapter

USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "").lower() in ("1", "true", "yes")

_adapter = SerperAdapter(api_key=os.environ.get("Serper_Api_Key"))


async def execute_web_search(query: str) -> str:
    if USE_MOCK_DATA:
        from fixtures.mock_data import get_mock_search_result
        return get_mock_search_result(query)
    return await _adapter.search(query)


async def execute_web_fetch(url: str) -> str:
    if USE_MOCK_DATA:
        return f"[Mock] {url}: World-class tourism destination with rich cultural heritage, diverse cuisine, and excellent transport links."
    return await _adapter.fetch(url)


async def execute_image_search(query: str) -> str | None:
    if USE_MOCK_DATA:
        return None
    return await _adapter.search_images(query)
