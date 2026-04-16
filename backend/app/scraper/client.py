"""Shared httpx client with rate limiting and retry logic."""
import asyncio
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://ygoprodeck.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def fetch_html(client: httpx.AsyncClient, url: str, retries: int = 3) -> Optional[str]:
    """Fetch a URL with retries and exponential backoff."""
    for attempt in range(retries):
        try:
            await asyncio.sleep(settings.scraper_delay_seconds)
            response = await client.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
            if response.status_code == 200:
                return response.text
            if response.status_code == 404:
                logger.warning("404 for %s", url)
                return None
            logger.warning("HTTP %s for %s (attempt %d)", response.status_code, url, attempt + 1)
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning("Request error for %s: %s (attempt %d)", url, e, attempt + 1)
        if attempt < retries - 1:
            await asyncio.sleep(2 ** attempt)
    logger.error("Failed to fetch %s after %d attempts", url, retries)
    return None


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        timeout=30,
    )
