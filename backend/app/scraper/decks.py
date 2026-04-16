"""Scrape individual deck pages from ygoprodeck.com/deck/<slug>."""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.scraper.client import BASE_URL, fetch_html

logger = logging.getLogger(__name__)


@dataclass
class CardEntry:
    card_id: int
    card_name: str
    card_type: Optional[str]
    zone: str  # "main", "extra", "side"
    quantity: int


@dataclass
class DeckData:
    deck_id: int
    slug: str
    archetype: Optional[str]
    deck_url: str
    cards: list[CardEntry] = field(default_factory=list)


# Keywords that uniquely identify extra deck card types across all ygoprodeck subtypes
# (e.g. "Link Effect Monster", "Synchro Tuner Monster", "Pendulum Effect Fusion Monster")
_EXTRA_DECK_KEYWORDS = {"fusion", "synchro", "xyz", "link"}


def _is_extra_deck_type(card_type: Optional[str]) -> bool:
    if not card_type:
        return False
    lower = card_type.lower()
    return "monster" in lower and any(kw in lower for kw in _EXTRA_DECK_KEYWORDS)


def _detect_zone(element, card_type: Optional[str] = None) -> str:
    """Walk up the DOM to find which zone (main/extra/side) a card element belongs to.

    ygoprodeck uses id attributes (id="main_deck", id="extra_deck", id="side_deck")
    to mark deck sections — not CSS classes. We check both id and class on each
    ancestor. Falls back to card_type keyword matching when the DOM walk is
    inconclusive (e.g. for extra deck card types like "Link Effect Monster").
    """
    el = element.parent
    depth = 0
    while el and depth < 15:
        # Check id attribute first — ygoprodeck uses id="main_deck" / "extra_deck" / "side_deck"
        el_id = el.get("id", "").lower()
        if "extra" in el_id:
            return "extra"
        if "side" in el_id:
            return "side"
        if "main" in el_id:
            return "main"

        # Also check class names as a fallback
        cls = " ".join(el.get("class", [])).lower()
        if "extra" in cls:
            return "extra"
        if "side" in cls:
            return "side"

        el = el.parent
        depth += 1

    # DOM walk was inconclusive — fall back to card type
    if _is_extra_deck_type(card_type):
        return "extra"
    return "main"


def parse_deck_page(html: str, slug: str) -> Optional[DeckData]:
    """Extract all cards from a deck detail page."""
    soup = BeautifulSoup(html, "lxml")

    # Extract numeric deck ID from slug (e.g. "exosister-694073" → 694073)
    id_match = re.search(r"-(\d+)$", slug)
    if not id_match:
        logger.warning("Could not extract deck ID from slug: %s", slug)
        return None
    deck_id = int(id_match.group(1))

    deck_url = f"{BASE_URL}/deck/{slug}"

    # Archetype: the page title or first badge
    title_tag = soup.find("h1") or soup.find("title")
    archetype = title_tag.get_text(strip=True).split(" - ")[0] if title_tag else None

    # Find all card elements — they carry data-card (ID) and data-cardname attributes
    card_elements = soup.find_all(attrs={"data-card": True, "data-cardname": True})
    if not card_elements:
        logger.warning("No card elements found on deck page: %s", slug)
        return None

    # Aggregate by (card_id, zone) to count copies
    aggregated: dict[tuple[int, str], CardEntry] = {}
    for el in card_elements:
        raw_id = el.get("data-card", "").strip()
        card_name = el.get("data-cardname", "").strip()
        card_type = el.get("data-cardtype", "").strip() or None

        if not raw_id or not card_name:
            continue

        try:
            card_id = int(raw_id)
        except ValueError:
            continue

        zone = _detect_zone(el, card_type)
        key = (card_id, zone)

        if key in aggregated:
            aggregated[key].quantity += 1
        else:
            aggregated[key] = CardEntry(
                card_id=card_id,
                card_name=card_name,
                card_type=card_type,
                zone=zone,
                quantity=1,
            )

    cards = list(aggregated.values())
    logger.debug("Deck %s: %d unique card entries across all zones", slug, len(cards))

    return DeckData(
        deck_id=deck_id,
        slug=slug,
        archetype=archetype,
        deck_url=deck_url,
        cards=cards,
    )


async def scrape_deck(client: httpx.AsyncClient, deck_slug: str) -> Optional[DeckData]:
    url = f"{BASE_URL}/deck/{deck_slug}"
    html = await fetch_html(client, url)
    if not html:
        return None
    return parse_deck_page(html, deck_slug)
