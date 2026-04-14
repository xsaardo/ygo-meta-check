"""Proxy to YGOPRODECK card API for autocomplete."""
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

CARD_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"


class CardSuggestion(BaseModel):
    id: int
    name: str
    type: str
    image_url_small: str
    archetype: Optional[str] = None


@router.get("/autocomplete", response_model=list[CardSuggestion])
async def autocomplete(
    q: str = Query(..., min_length=2, description="Partial card name"),
):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(CARD_API, params={"fname": q, "num": 10, "offset": 0})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, KeyError, ValueError):
            return []

    suggestions = []
    for card in data.get("data", [])[:10]:
        images = card.get("card_images", [])
        if not images:
            continue
        suggestions.append(
            CardSuggestion(
                id=card["id"],
                name=card["name"],
                type=card.get("type", ""),
                image_url_small=images[0]["image_url_small"],
                archetype=card.get("archetype"),
            )
        )
    return suggestions
