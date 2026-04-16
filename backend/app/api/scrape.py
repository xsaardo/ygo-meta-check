"""Manual scrape trigger endpoint (dev/admin use)."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.scraper.runner import run_scrape, rescrape_deck_cards
from app.scraper.cards import sync_cards

router = APIRouter()
logger = logging.getLogger(__name__)

_scrape_running = False
_card_sync_running = False


@router.post("/scrape/trigger")
async def trigger_scrape():
    global _scrape_running

    if not settings.allow_manual_scrape:
        raise HTTPException(status_code=403, detail="Manual scrape trigger is disabled")

    if _scrape_running:
        raise HTTPException(status_code=409, detail="A scrape is already running")

    async def _run():
        global _scrape_running
        _scrape_running = True
        try:
            result = await run_scrape()
            logger.info("Manual scrape completed: %s", result)
        finally:
            _scrape_running = False

    asyncio.create_task(_run())
    return {"message": "Scrape started in background"}


@router.get("/scrape/status")
async def scrape_status():
    return {"running": _scrape_running}


_rescrape_running = False


@router.post("/scrape/rescrape-deck-cards")
async def trigger_rescrape_deck_cards():
    """Re-scrape all deck cards to fix zone classification (e.g. after scraper bug fix)."""
    global _rescrape_running

    if not settings.allow_manual_scrape:
        raise HTTPException(status_code=403, detail="Manual scrape trigger is disabled")

    if _rescrape_running:
        raise HTTPException(status_code=409, detail="A rescrape is already running")

    async def _run():
        global _rescrape_running
        _rescrape_running = True
        try:
            result = await rescrape_deck_cards()
            logger.info("Deck cards rescrape completed: %s", result)
        finally:
            _rescrape_running = False

    asyncio.create_task(_run())
    return {"message": "Deck cards rescrape started in background"}


@router.get("/scrape/rescrape-deck-cards/status")
async def rescrape_deck_cards_status():
    return {"running": _rescrape_running}


@router.post("/cards/sync")
async def trigger_card_sync():
    global _card_sync_running

    if not settings.allow_manual_scrape:
        raise HTTPException(status_code=403, detail="Manual triggers are disabled")

    if _card_sync_running:
        raise HTTPException(status_code=409, detail="Card sync is already running")

    async def _run():
        global _card_sync_running
        _card_sync_running = True
        try:
            result = await sync_cards()
            logger.info("Card sync completed: %s", result)
        finally:
            _card_sync_running = False

    asyncio.create_task(_run())
    return {"message": "Card sync started in background"}


@router.get("/cards/sync/status")
async def card_sync_status():
    return {"running": _card_sync_running}
