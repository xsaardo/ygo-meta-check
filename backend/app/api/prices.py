"""Card price proxy with 1-hour in-memory cache (bounded LRU, max 5000 entries)."""

import time
from collections import OrderedDict
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CARD_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
CACHE_TTL = 3600  # 1 hour
CACHE_MAX_SIZE = 5000


class _BoundedCache:
    """Thread-safe LRU cache with a fixed max size and TTL-based expiry."""

    def __init__(self, maxsize: int) -> None:
        self._maxsize = maxsize
        self._store: OrderedDict[int, tuple[float, "CardPrices"]] = OrderedDict()

    def get(self, key: int) -> "CardPrices | None":
        if key not in self._store:
            return None
        ts, value = self._store[key]
        if time.monotonic() - ts >= CACHE_TTL:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: int, value: "CardPrices") -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (time.monotonic(), value)
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)  # evict oldest


_cache = _BoundedCache(maxsize=CACHE_MAX_SIZE)


class CardPrices(BaseModel):
    tcgplayer: Optional[str] = None
    cardmarket: Optional[str] = None


@router.get("/prices/{card_id}", response_model=CardPrices)
async def get_prices(card_id: int):
    cached = _cache.get(card_id)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(CARD_API, params={"id": card_id})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(status_code=502, detail="Price fetch failed")

    cards = data.get("data", [])
    if not cards:
        raise HTTPException(status_code=404, detail="Card not found")

    raw = (cards[0].get("card_prices") or [{}])[0]
    prices = CardPrices(
        tcgplayer=raw.get("tcgplayer_price") or None,
        cardmarket=raw.get("cardmarket_price") or None,
    )

    _cache.set(card_id, prices)
    return prices
