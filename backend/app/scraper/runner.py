"""Orchestrates the full scrape: tournaments → placements → decks → cards."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Deck, DeckCard, Placement, Tournament
from app.scraper.client import make_client
from app.scraper.decks import scrape_deck
from app.scraper.tournaments import scrape_tournament_detail, scrape_tournament_listing

logger = logging.getLogger(__name__)


async def _upsert_tournament(session: AsyncSession, row) -> Tournament:
    result = await session.execute(
        select(Tournament).where(Tournament.ygopro_id == row.ygopro_id)
    )
    tournament = result.scalar_one_or_none()
    if tournament is None:
        tournament = Tournament(
            ygopro_id=row.ygopro_id,
            slug=row.slug,
            name=row.name,
            date=row.date,
            country=row.country,
            player_count=row.player_count,
            tier=row.tier,
            format=row.format,
        )
        session.add(tournament)
    else:
        tournament.name = row.name
        tournament.country = row.country
        tournament.player_count = row.player_count
    await session.flush()
    return tournament


async def _upsert_deck(session: AsyncSession, deck_data) -> Deck:
    result = await session.execute(
        select(Deck).where(Deck.ygopro_id == deck_data.deck_id)
    )
    deck = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if deck is None:
        deck = Deck(
            ygopro_id=deck_data.deck_id,
            slug=deck_data.slug,
            archetype=deck_data.archetype,
            deck_url=deck_data.deck_url,
            scraped_at=now,
        )
        session.add(deck)
        await session.flush()

        # Insert cards
        for card in deck_data.cards:
            session.add(
                DeckCard(
                    deck_id=deck.id,
                    card_id=card.card_id,
                    card_name=card.card_name,
                    card_type=card.card_type,
                    zone=card.zone,
                    quantity=card.quantity,
                )
            )
    else:
        # Already scraped — skip re-scraping cards (deck lists don't change)
        pass
    await session.flush()
    return deck


async def _process_tournament(client, tournament_row) -> None:
    """Scrape a single tournament's placements and decks, saving to DB."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Upsert tournament
            tournament = await _upsert_tournament(session, tournament_row)

            # Check if we already have placements for this tournament
            existing = await session.execute(
                select(Placement)
                .where(Placement.tournament_id == tournament.id)
                .limit(1)
            )
            if existing.scalar_one_or_none():
                logger.debug(
                    "Tournament %s already has placements, skipping",
                    tournament_row.slug,
                )
                return

            # Scrape placement rows
            placements = await scrape_tournament_detail(client, tournament_row.slug)
            if not placements:
                tournament.scraped_at = datetime.now(timezone.utc)
                return

            # Scrape each deck concurrently (up to workers limit)
            sem = asyncio.Semaphore(settings.scraper_workers)

            async def fetch_and_save_deck(placement_row):
                async with sem:
                    deck_data = await scrape_deck(client, placement_row.deck_slug)
                    if not deck_data:
                        return None
                    return deck_data

            deck_results = await asyncio.gather(
                *[fetch_and_save_deck(p) for p in placements],
                return_exceptions=True,
            )

            # Save decks and placements
            for placement_row, deck_data in zip(placements, deck_results):
                if isinstance(deck_data, Exception) or deck_data is None:
                    continue

                deck = await _upsert_deck(session, deck_data)
                session.add(
                    Placement(
                        tournament_id=tournament.id,
                        deck_id=deck.id,
                        placement=placement_row.placement,
                        player_name=placement_row.player_name,
                    )
                )

            tournament.scraped_at = datetime.now(timezone.utc)

    logger.info("Saved tournament: %s", tournament_row.name)


async def rescrape_deck_cards() -> dict:
    """Re-scrape cards for all existing decks, replacing stored deck_cards.

    Use this when the zone detection logic has been fixed and existing data
    needs to be corrected (e.g. side/extra cards stored as 'main').
    """
    logger.info("Starting full deck cards rescrape")
    start = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Deck.id, Deck.slug))
        decks = result.all()

    logger.info("Re-scraping cards for %d decks", len(decks))
    sem = asyncio.Semaphore(settings.scraper_workers)
    success = 0
    failed = 0

    async def _rescrape_one(deck_id: int, slug: str) -> None:
        nonlocal success, failed
        async with sem:
            async with make_client() as client:
                deck_data = await scrape_deck(client, slug)
            if not deck_data:
                failed += 1
                return
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    # Delete existing cards and re-insert with corrected zones
                    await session.execute(
                        delete(DeckCard).where(DeckCard.deck_id == deck_id)
                    )
                    for card in deck_data.cards:
                        session.add(
                            DeckCard(
                                deck_id=deck_id,
                                card_id=card.card_id,
                                card_name=card.card_name,
                                card_type=card.card_type,
                                zone=card.zone,
                                quantity=card.quantity,
                            )
                        )
            success += 1

    await asyncio.gather(*[_rescrape_one(d.id, d.slug) for d in decks])

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(
        "Deck cards rescrape complete: %d ok, %d failed in %.1fs",
        success,
        failed,
        elapsed,
    )
    return {
        "decks_total": len(decks),
        "success": success,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 1),
    }


async def run_scrape() -> dict:
    """Main entry point: scrape all recent tournaments."""
    logger.info("Starting scrape run")
    start = datetime.now(timezone.utc)

    async with make_client() as client:
        # Step 1: get tournament listing
        tournament_rows = await scrape_tournament_listing(client)
        logger.info(
            "Found %d tournaments in the last %d months",
            len(tournament_rows),
            settings.scraper_months_lookback,
        )

        # Step 2: process tournaments concurrently
        sem = asyncio.Semaphore(settings.scraper_workers)

        async def process_with_sem(row):
            async with sem:
                try:
                    await _process_tournament(client, row)
                except Exception as e:
                    logger.error("Error processing tournament %s: %s", row.slug, e)

        await asyncio.gather(*[process_with_sem(row) for row in tournament_rows])

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("Scrape complete in %.1fs", elapsed)
    return {
        "tournaments_found": len(tournament_rows),
        "elapsed_seconds": round(elapsed, 1),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
