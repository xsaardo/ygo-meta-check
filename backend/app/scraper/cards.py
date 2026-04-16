"""Bulk card sync: fetches all ~12k cards from YGOPRODECK and stores them locally."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Card

logger = logging.getLogger(__name__)

CARD_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
IMAGE_CONCURRENCY = 10  # parallel image downloads


async def _download_image(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    card_id: int,
    url: str,
    images_dir: Path,
) -> str | None:
    dest = images_dir / f"{card_id}.jpg"
    if dest.exists():
        return str(dest.relative_to(images_dir.parent))

    async with sem:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return str(dest.relative_to(images_dir.parent))
        except Exception as exc:
            logger.warning("Image download failed for card %d: %s", card_id, exc)
            return None


async def sync_cards() -> dict:
    """
    Fetch all cards from YGOPRODECK, upsert into the local `cards` table,
    and download small card images to disk.
    """
    images_dir = Path(settings.card_images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching full card list from YGOPRODECK…")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(CARD_API, params={"misc": "yes"})
            resp.raise_for_status()
            raw_cards = resp.json().get("data", [])
        except Exception as exc:
            logger.error("Failed to fetch card list: %s", exc)
            return {"error": str(exc)}

    logger.info("Fetched %d cards — downloading images…", len(raw_cards))

    sem = asyncio.Semaphore(IMAGE_CONCURRENCY)
    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient(timeout=10) as img_client:
        card_image_urls: list[tuple[int, str]] = []
        for card in raw_cards:
            images = card.get("card_images", [])
            if images:
                card_image_urls.append((card["id"], images[0]["image_url_small"]))

        image_results = await asyncio.gather(
            *[
                _download_image(img_client, sem, card_id, url, images_dir)
                for card_id, url in card_image_urls
            ]
        )

    # Map card_id → image_path
    image_map: dict[int, str | None] = {
        card_id: path for (card_id, _), path in zip(card_image_urls, image_results)
    }

    # Upsert all cards
    rows = [
        {
            "id": card["id"],
            "name": card["name"],
            "type": card.get("type", ""),
            "archetype": card.get("archetype"),
            "image_path": image_map.get(card["id"]),
            "synced_at": now,
        }
        for card in raw_cards
    ]

    # PostgreSQL caps prepared-statement parameters at 65535.
    # Each row uses 6 columns, so keep batches well under that limit.
    BATCH_SIZE = 1000
    async with AsyncSessionLocal() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            stmt = insert(Card).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": stmt.excluded.name,
                    "type": stmt.excluded.type,
                    "archetype": stmt.excluded.archetype,
                    "image_path": stmt.excluded.image_path,
                    "synced_at": stmt.excluded.synced_at,
                },
            )
            await session.execute(stmt)
        await session.commit()

    downloaded = sum(1 for p in image_results if p)
    logger.info("Card sync complete: %d cards, %d images", len(rows), downloaded)
    return {"cards": len(rows), "images_downloaded": downloaded}
