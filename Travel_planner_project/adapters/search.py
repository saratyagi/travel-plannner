import httpx
from cachetools import TTLCache


class SerperAdapter:
    _SEARCH_URL = "https://google.serper.dev/search"
    _IMAGES_URL = "https://google.serper.dev/images"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._search_cache: TTLCache = TTLCache(maxsize=256, ttl=3600)
        self._fetch_cache: TTLCache = TTLCache(maxsize=256, ttl=3600)
        self._image_cache: TTLCache = TTLCache(maxsize=128, ttl=3600)

    async def search(self, query: str) -> str:
        if query in self._search_cache:
            return self._search_cache[query]
        if not self._api_key:
            return "Web search unavailable: Serper_Api_Key not configured."
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._SEARCH_URL,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
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
                parts.append(
                    f"• {r.get('title', '')}: {r.get('snippet', '')} [Source: {r.get('link', '')}]"
                )
            result = "\n".join(parts) if parts else "No results found."
            self._search_cache[query] = result
            return result
        except Exception as e:
            return f"Search error: {e}"

    async def fetch(self, url: str) -> str:
        if url in self._fetch_cache:
            return self._fetch_cache[url]
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; TravelPlanner/1.0)"},
                )
                response.raise_for_status()
                result = response.text[:2000]
                self._fetch_cache[url] = result
                return result
        except Exception as e:
            return f"Fetch error: {e}"

    async def search_images(self, query: str) -> str | None:
        if query in self._image_cache:
            return self._image_cache[query]
        if not self._api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    self._IMAGES_URL,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 5},
                )
                resp.raise_for_status()
                for img in resp.json().get("images", []):
                    url = img.get("imageUrl", "")
                    if url and url.startswith("http") and not url.endswith(".svg"):
                        self._image_cache[query] = url
                        return url
            self._image_cache[query] = None
            return None
        except Exception:
            self._image_cache[query] = None
            return None
