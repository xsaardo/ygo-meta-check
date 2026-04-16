---
module: YGO Meta Check Scraper
date: 2026-04-15
problem_type: database_issue
component: database
symptoms:
  - "Extra Deck filter returns 'Not in Recent Meta' for known extra deck cards"
  - "All Zones returns results but zone badge shows 'Main' for Fusion/Synchro/XYZ/Link monsters"
  - "API request with zone=extra returns 0 results despite card appearing in tournament decks"
root_cause: logic_error
resolution_type: code_fix
severity: high
tags: [zone-detection, scraper, extra-deck, card-type, data-fix]
---

# Troubleshooting: Extra Deck Cards Stored as zone='main' by Scraper

## Problem

When searching for extra deck cards (Link, Fusion, Synchro, XYZ monsters), selecting the "Extra Deck" zone filter showed no results — but "All Zones" returned results with zone badges incorrectly labeled "Main". The scraper was storing all extra deck cards as `zone='main'` due to a DOM walking failure and an overly strict card type fallback.

## Environment

- Module: YGO Meta Check Scraper
- Affected Component: `backend/app/scraper/decks.py` — `_detect_zone()` function
- Database: `deck_cards` table, `zone` column
- Date: 2026-04-15

## Symptoms

- Searching Accesscode Talker (Link Monster) with "Extra Deck" filter: "NOT IN RECENT META — No tournament appearances found"
- Switching to "All Zones": 108 appearances found, all with zone badge "Main"
- API request: `GET /api/search?card=Accesscode+Talker&months=3&zone=extra` → `total_appearances: 0`
- API request: `GET /api/search?card=Accesscode+Talker&months=3` (no zone) → `total_appearances: 108`

## What Didn't Work

**Attempted Solution 1:** Suspected frontend type detection (EXTRA_DECK_TYPES set)
- Checked that `detectZone("Link Monster")` returned `"extra"` — it did
- Browser automation confirmed the API was correctly sending `zone=extra`
- **Why it failed:** The frontend was correct; issue was in stored data

**Attempted Solution 2:** Migration with exact `card_type IN (...)` matching
- Created migration matching `card_type IN ('Link Monster', 'Fusion Monster', ...)`
- Ran migration — `UPDATE 0` rows affected
- **Why it failed:** ygoprodeck stores subtypes like `"Link Effect Monster"`, not plain `"Link Monster"`. Exact string match missed all real rows.

## Solution

**Two-part fix:**

### 1. Scraper code fix (`backend/app/scraper/decks.py`)

Added keyword-based fallback in `_detect_zone` and passed `card_type` through:

```python
# Before (broken):
def _detect_zone(element) -> str:
    el = element.parent
    depth = 0
    while el and depth < 15:
        cls = " ".join(el.get("class", []))
        if "side" in cls.lower():
            return "side"
        if "extra" in cls.lower():
            return "extra"
        el = el.parent
        depth += 1
    return "main"  # ← fell through for all extra deck cards

# After (fixed):
_EXTRA_DECK_KEYWORDS = {"fusion", "synchro", "xyz", "link"}

def _is_extra_deck_type(card_type: Optional[str]) -> bool:
    if not card_type:
        return False
    lower = card_type.lower()
    return "monster" in lower and any(kw in lower for kw in _EXTRA_DECK_KEYWORDS)

def _detect_zone(element, card_type: Optional[str] = None) -> str:
    el = element.parent
    depth = 0
    while el and depth < 15:
        cls = " ".join(el.get("class", []))
        if "extra" in cls.lower():  # check extra BEFORE side
            return "extra"
        if "side" in cls.lower():
            return "side"
        el = el.parent
        depth += 1
    # Fallback: use card_type keywords
    if _is_extra_deck_type(card_type):
        return "extra"
    return "main"

# Call site updated to pass card_type:
zone = _detect_zone(el, card_type)
```

### 2. Data fix migration (`backend/alembic/versions/0003_fix_extra_deck_zones.py`)

Used ILIKE pattern matching instead of exact string comparison:

```python
def upgrade() -> None:
    op.execute(
        """
        UPDATE deck_cards
        SET zone = 'extra'
        WHERE zone = 'main'
          AND (
            card_type ILIKE '%Fusion%Monster%'
            OR card_type ILIKE '%Synchro%Monster%'
            OR card_type ILIKE '%XYZ%Monster%'
            OR card_type ILIKE '%Link%Monster%'
          )
        """
    )
```

**Result:** All 109 Accesscode Talker rows (and all other wrongly-classified extra deck cards) corrected to `zone='extra'`.

## Why This Works

**Root cause:** ygoprodeck's deck page HTML structure doesn't consistently place "extra" in CSS class names in the path from a card element to the document root. When the DOM walk exhausted 15 parent levels without finding "extra" or "side", `_detect_zone` defaulted to "main" for every extra deck card.

The original card-type fallback used exact string matching (`card_type in {"fusion monster", ...}`) but ygoprodeck stores nuanced subtypes: `"Link Effect Monster"`, `"Synchro Tuner Monster"`, `"XYZ Pendulum Effect Monster"`, etc. None matched exactly.

The fix uses keyword substring matching — the words "fusion", "synchro", "xyz", and "link" appear in ALL extra deck type strings and in NO main deck type strings, making them reliable discriminators regardless of subtype suffix.

## Prevention

- **Never use exact string matching for external card type values** — ygoprodeck appends effect/tuner/pendulum subtypes that vary per card. Use substring/keyword matching instead.
- **When writing DB fix migrations, verify row counts first**: run a `SELECT COUNT(*)` with the same WHERE clause before committing to confirm it will actually match rows.
- **Confirm data in DB before diagnosing frontend**: use browser network tools to see the exact API request+response first. In this case, seeing `zone=extra` in the request URL immediately pointed to the data layer.

## Related Issues

- See also: [autocomplete-500-alembic-migration-not-applied-backend-20260415.md](./autocomplete-500-alembic-migration-not-applied-backend-20260415.md)
