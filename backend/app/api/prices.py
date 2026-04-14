"""Card price proxy with 1-hour in-memory cache."""
import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CARD_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
CACHE_TTL = 3600  # 1 hour

_cache: dict[int, tuple[float, "CardPrices"]] = {}


class CardPrices(BaseModel):
    tcgplayer: Optional[str] = None
    cardmarket: Optional[str] = None


@router.get("/prices/{card_id}", response_model=CardPrices)
async def get_prices(card_id: int):
    now = time.monotonic()
    if card_id in _cache:
        ts, prices = _cache[card_id]
        if now - ts < CACHE_TTL:
            return prices

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

    _cache[card_id] = (now, prices)
    return prices
