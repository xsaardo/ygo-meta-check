"""Scrape the ygoprodeck.com/tournaments/ listing page."""
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.scraper.client import BASE_URL, fetch_html

logger = logging.getLogger(__name__)

SLUG_ID_RE = re.compile(r"-(\d+)$")


@dataclass
class TournamentRow:
    ygopro_id: int
    slug: str
    name: str
    date: date
    country: Optional[str]
    player_count: Optional[int]
    tier: Optional[int]
    format: Optional[str]


@dataclass
class PlacementRow:
    placement: str
    player_name: Optional[str]
    deck_slug: Optional[str]   # e.g. "exosister-694073"
    deck_id: Optional[int]
    archetype: Optional[str]


def _parse_player_count(text: str) -> Optional[int]:
    """Extract numeric player count, handling '~200' style strings."""
    cleaned = text.strip().lstrip("~").replace(",", "")
    try:
        return int(cleaned)
    except ValueError:
        return None


def _extract_id_from_slug(slug: str) -> Optional[int]:
    match = SLUG_ID_RE.search(slug)
    return int(match.group(1)) if match else None


def parse_tournament_listing(html: str, cutoff_date: date) -> list[TournamentRow]:
    """Parse all tournament rows from the /tournaments/ listing page."""
    soup = BeautifulSoup(html, "lxml")
    rows = []

    # DataTables renders all rows in the HTML; each row is a <tr> inside the main table
    table = soup.find("table", id=lambda x: x and "tournament" in x.lower()) or soup.find("table")
    if not table:
        logger.error("Could not find tournament table in listing page")
        return rows

    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue

        # Find the tournament link in the row
        link = tr.find("a", href=re.compile(r"/tournament/"))
        if not link:
            continue

        href = link.get("href", "")
        # href is like /tournament/rochester-wcq-regional-4470
        slug = href.strip("/").split("/")[-1]
        ygopro_id = _extract_id_from_slug(slug)
        if not ygopro_id:
            continue

        name = link.get_text(strip=True)

        # Date is typically in the first cell — formats: "2026-04-11" or "Apr 11, 2026"
        date_text = cells[0].get_text(strip=True)
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(date_text, fmt).date()
                break
            except ValueError:
                continue
        if parsed_date is None:
            logger.debug("Could not parse date %r, skipping row", date_text)
            continue

        if parsed_date < cutoff_date:
            continue  # Skip tournaments older than the lookback window

        # Country flag cell — grab the title attribute of the flag span
        country_span = tr.find("span", class_="country-flag")
        country = country_span.get("title") if country_span else None

        # Player count
        player_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        player_count = _parse_player_count(player_text)

        rows.append(
            TournamentRow(
                ygopro_id=ygopro_id,
                slug=slug,
                name=name,
                date=parsed_date,
                country=country,
                player_count=player_count,
                tier=None,   # Not reliably in the listing; parsed from detail page
                format=None,
            )
        )

    logger.info("Parsed %d tournaments from listing (since %s)", len(rows), cutoff_date)
    return rows


def parse_tournament_detail(html: str, tournament_slug: str) -> list[PlacementRow]:
    """Parse placement rows with deck links from a /tournament/<slug> page."""
    soup = BeautifulSoup(html, "lxml")
    placements = []

    rows = soup.find_all("a", class_="tournament_table_row")
    if not rows:
        # Fall back to non-anchor rows
        rows = soup.find_all(attrs={"class": "tournament_table_row"})

    for row in rows:
        # Deck URL
        deck_url = row.get("data-deckurl") or row.get("href")
        if not deck_url:
            continue  # Skip rows without a submitted decklist

        # Extract deck slug: /deck/exosister-694073 → exosister-694073
        deck_slug = deck_url.strip("/").split("/")[-1]
        deck_id = _extract_id_from_slug(deck_slug)
        if not deck_id:
            continue

        # Placement
        bold = row.find("b")
        placement = bold.get_text(strip=True) if bold else "Unknown"

        # Player name
        player_span = row.find("span", class_="player-name")
        player_name = player_span.get_text(strip=True) if player_span else None
        if player_name in ("<unknown duelist>", ""):
            player_name = None

        # Primary archetype (first badge)
        badge = row.find("span", class_="badge-ygoprodeck")
        archetype = badge.get_text(strip=True) if badge else None

        placements.append(
            PlacementRow(
                placement=placement,
                player_name=player_name,
                deck_slug=deck_slug,
                deck_id=deck_id,
                archetype=archetype,
            )
        )

    logger.info(
        "Tournament %s: found %d placements with decklists", tournament_slug, len(placements)
    )
    return placements


TOURNAMENTS_API_URL = "https://ygoprodeck.com/api/tournament/getTournaments.php"


async def scrape_tournament_listing(client: httpx.AsyncClient) -> list[TournamentRow]:
    cutoff = date.today() - timedelta(days=settings.scraper_months_lookback * 30)
    try:
        resp = await client.get(
            TOURNAMENTS_API_URL,
            headers={"Accept": "application/json", "Referer": f"{BASE_URL}/tournaments/"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch tournament JSON API: %s", exc)
        return []

    rows = []
    for item in data.get("data", []):
        try:
            event_date = date.fromisoformat(item["event_date"])
        except (KeyError, ValueError):
            logger.debug("Skipping item with bad date: %r", item)
            continue

        if event_date < cutoff:
            continue

        slug = item.get("slug", "")
        ygopro_id = item.get("id") or _extract_id_from_slug(slug)
        if not ygopro_id:
            continue

        player_count = item.get("player_count")
        if item.get("is_approximate_player_count") and player_count:
            # Keep the value but note it's approximate (already stored as int)
            pass

        rows.append(
            TournamentRow(
                ygopro_id=int(ygopro_id),
                slug=slug,
                name=item.get("name", ""),
                date=event_date,
                country=item.get("country"),
                player_count=int(player_count) if player_count else None,
                tier=None,
                format=item.get("format"),
            )
        )

    logger.info("Fetched %d tournaments from API (since %s)", len(rows), cutoff)
    return rows


async def scrape_tournament_detail(
    client: httpx.AsyncClient, slug: str
) -> list[PlacementRow]:
    url = f"{BASE_URL}/tournament/{slug}"
    html = await fetch_html(client, url)
    if not html:
        return []
    return parse_tournament_detail(html, slug)
