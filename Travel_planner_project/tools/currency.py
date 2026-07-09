import os
import time
import httpx

FALLBACK_RATE = 84.0
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "").lower() in ("1", "true", "yes")

_cache: tuple[float, float] | None = None  # (rate, fetch_timestamp)
_CACHE_TTL = 86400.0  # 24 hours


async def get_usd_to_inr() -> float:
    global _cache
    if USE_MOCK_DATA:
        return FALLBACK_RATE
    if _cache is not None and (time.time() - _cache[1]) < _CACHE_TTL:
        return _cache[0]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://open.er-api.com/v6/latest/USD")
            resp.raise_for_status()
            rate = float(resp.json()["rates"]["INR"])
            _cache = (rate, time.time())
            return rate
    except Exception:
        return FALLBACK_RATE
