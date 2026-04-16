"""Card search and meta relevance API."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DeckCard, Deck, Placement, Tournament

router = APIRouter()


class DeckAppearance(BaseModel):
    tournament_name: str
    tournament_date: date
    tournament_url: str
    placement: Optional[str]
    player_name: Optional[str]
    deck_archetype: Optional[str]
    deck_url: str
    card_zone: str
    card_quantity: int
    format: Optional[str] = None


class SearchResult(BaseModel):
    card_name: str
    meta_relevant: bool
    total_appearances: int
    results: list[DeckAppearance]


@router.get("/search", response_model=SearchResult)
async def search_card(
    card: str = Query(..., min_length=2, description="Card name to search for"),
    months: int = Query(3, ge=1, le=12, description="Lookback window in months"),
    zone: Optional[str] = Query(None, description="Filter by zone: main, extra, side"),
    db: AsyncSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=months * 30)

    stmt = (
        select(
            DeckCard.card_name,
            DeckCard.zone,
            DeckCard.quantity,
            Deck.archetype,
            Deck.deck_url,
            Placement.placement,
            Placement.player_name,
            Tournament.name.label("tournament_name"),
            Tournament.date.label("tournament_date"),
            Tournament.slug.label("tournament_slug"),
            Tournament.format.label("tournament_format"),
        )
        .join(Deck, DeckCard.deck_id == Deck.id)
        .join(Placement, Placement.deck_id == Deck.id)
        .join(Tournament, Placement.tournament_id == Tournament.id)
        .where(func.lower(DeckCard.card_name) == func.lower(card))
        .where(Tournament.date >= cutoff)
        .order_by(Tournament.date.desc())
    )

    if zone:
        stmt = stmt.where(DeckCard.zone == zone)

    rows = (await db.execute(stmt)).all()

    appearances = [
        DeckAppearance(
            tournament_name=r.tournament_name,
            tournament_date=r.tournament_date,
            tournament_url=f"https://ygoprodeck.com/tournament/{r.tournament_slug}",
            placement=r.placement,
            player_name=r.player_name,
            deck_archetype=r.archetype,
            deck_url=r.deck_url,
            card_zone=r.zone,
            card_quantity=r.quantity,
            format=r.tournament_format,
        )
        for r in rows
    ]

    return SearchResult(
        card_name=card,
        meta_relevant=len(appearances) > 0,
        total_appearances=len(appearances),
        results=appearances,
    )


class StatsResult(BaseModel):
    tournament_count: int
    deck_count: int
    card_entry_count: int
    oldest_tournament: Optional[date]
    newest_tournament: Optional[date]


@router.get("/stats", response_model=StatsResult)
async def get_stats(db: AsyncSession = Depends(get_db)):
    t_count = (
        await db.execute(select(func.count()).select_from(Tournament))
    ).scalar_one()
    d_count = (await db.execute(select(func.count()).select_from(Deck))).scalar_one()
    c_count = (
        await db.execute(select(func.count()).select_from(DeckCard))
    ).scalar_one()

    date_result = await db.execute(
        select(func.min(Tournament.date), func.max(Tournament.date))
    )
    oldest, newest = date_result.one()

    return StatsResult(
        tournament_count=t_count,
        deck_count=d_count,
        card_entry_count=c_count,
        oldest_tournament=oldest,
        newest_tournament=newest,
    )
