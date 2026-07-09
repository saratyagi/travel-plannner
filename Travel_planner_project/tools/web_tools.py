import os
import httpx

SERPER_API_KEY = os.environ.get("Serper_Api_Key")
SERPER_URL = "https://google.serper.dev/search"
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "").lower() in ("1", "true", "yes")

_search_cache: dict[str, str] = {}
_fetch_cache: dict[str, str] = {}


async def execute_web_search(query: str) -> str:
    if USE_MOCK_DATA:
        from tools.mock_data import get_mock_search_result
        return get_mock_search_result(query)
    if query in _search_cache:
        return _search_cache[query]
    if not SERPER_API_KEY:
        return "Web search unavailable: Serper_Api_Key not configured."
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                SERPER_URL,
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 5},
            )
            response.raise_for_status()
            data = response.json()

        parts: list[str] = []

        if ab := data.get("answerBox"):
            parts.append(f"Featured answer: {ab.get('answer', ab.get('snippet', ''))}")

        if kg := data.get("knowledgeGraph"):
            if desc := kg.get("description"):
                parts.append(f"Knowledge graph: {desc}")

        for r in data.get("organic", [])[:5]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            parts.append(f"• {title}: {snippet} [Source: {link}]")

        result = "\n".join(parts) if parts else "No results found."
        _search_cache[query] = result
        return result
    except Exception as e:
        return f"Search error: {e}"


async def execute_web_fetch(url: str) -> str:
    if USE_MOCK_DATA:
        return f"[Mock] {url}: World-class tourism destination with rich cultural heritage, diverse cuisine, and excellent transport links."
    if url in _fetch_cache:
        return _fetch_cache[url]
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TravelPlanner/1.0)"},
            )
            response.raise_for_status()
            result = response.text[:2000]
            _fetch_cache[url] = result
            return result
    except Exception as e:
        return f"Fetch error: {e}"
