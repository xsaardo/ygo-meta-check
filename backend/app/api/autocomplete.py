"""Card autocomplete backed by the local cards table (with pg_trgm fallback to YGOPRODECK)."""
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Card

router = APIRouter()

CARD_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"


class CardSuggestion(BaseModel):
    id: int
    name: str
    type: str
    image_url_small: str
    archetype: Optional[str] = None


def _image_url(card: Card) -> str:
    """Return a local image URL if the image is on disk, else fall back to YGOPRODECK CDN."""
    if card.image_path:
        p = Path(settings.card_images_dir) / f"{card.id}.jpg"
        if p.exists():
            return f"/static/cards/{card.id}.jpg"
    return f"https://images.ygoprodeck.com/images/cards_small/{card.id}.jpg"


async def _local_autocomplete(q: str, db: AsyncSession) -> list[CardSuggestion]:
    """Query the local cards table using trigram similarity ranking."""
    stmt = (
        select(Card)
        .where(Card.name.ilike(f"%{q}%"))
        .order_by(
            # Prefer names that start with the query
            func.lower(Card.name).startswith(func.lower(q)).desc(),
            # Then sort alphabetically
            Card.name,
        )
        .limit(10)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        CardSuggestion(
            id=c.id,
            name=c.name,
            type=c.type,
            image_url_small=_image_url(c),
            archetype=c.archetype,
        )
        for c in rows
    ]


async def _remote_autocomplete(q: str) -> list[CardSuggestion]:
    """Fallback: proxy to YGOPRODECK when local card table is empty."""
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
        image_url = images[0].get("image_url_small", "")
        if not image_url.startswith("https://images.ygoprodeck.com/"):
            continue
        suggestions.append(
            CardSuggestion(
                id=card["id"],
                name=card["name"],
                type=card.get("type", ""),
                image_url_small=image_url,
                archetype=card.get("archetype"),
            )
        )
    return suggestions


@router.get("/autocomplete", response_model=list[CardSuggestion])
async def autocomplete(
    q: str = Query(..., min_length=2, description="Partial card name"),
    db: AsyncSession = Depends(get_db),
):
    # Check if the local cards table exists and has been populated
    try:
        count = (await db.execute(select(func.count()).select_from(Card))).scalar_one()
    except Exception:
        # Table doesn't exist yet (migration pending) — fall back to live API
        await db.rollback()
        return await _remote_autocomplete(q)

    if count > 0:
        return await _local_autocomplete(q, db)
    # Fall back to live API proxy until the card sync job has run
    return await _remote_autocomplete(q)
