"""APScheduler weekly cron job for scraping."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.scraper.runner import run_scrape

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def init_scheduler():
    """Register the weekly scrape job. Runs every Sunday at 03:00 UTC."""
    scheduler.add_job(
        run_scrape,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="UTC"),
        id="weekly_scrape",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("Scheduler started — weekly scrape every Sunday at 03:00 UTC")
