"""Manual scrape trigger endpoint (dev/admin use)."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.scraper.runner import run_scrape

router = APIRouter()
logger = logging.getLogger(__name__)

_scrape_running = False


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
