---
date: 2026-04-13
topic: ygo-meta-check
---

# YGO Meta Check

## What We're Building

A public web app where users search for a Yu-Gi-Oh! card by name and instantly see whether it has appeared in any tournament decklist in the past N months. Results link back to the specific tournament and deck on ygoprodeck.com. The primary use case is checking a card's competitive value at a card shop before buying or selling.

Data source: ygoprodeck.com/tournaments/ — scraped weekly and stored locally so searches are fast and don't depend on their uptime.

## Why This Approach

Three approaches were considered:

- **A. Card-level search with local DB** — scrape tournaments weekly into Postgres, search by individual card name. Chosen.
- **B. Archetype-level only** — simpler scrape but too coarse; "is Branded Fusion meta?" doesn't help price a specific card.
- **C. Live scrape on demand** — no DB, scrape ygoprodeck on each user search. Too slow, not scalable, and violates their API terms.

Approach A was chosen because it supports the primary use case (individual card valuation), scales to multiple users, and sets up a future price-tracking feature naturally.

## Key Decisions

- **Search by individual card name**, not archetype — the goal is to price a specific card, not evaluate a strategy
- **Only include placements with submitted decklists** — appearances without a decklist are useless for card-level search
- **Weekly scraper cadence** — tournaments happen on weekends; weekly is fresh enough without hammering their site
- **Postgres 16** — needed for full-text/trigram search and to support concurrent users; SQLite ruled out
- **FastAPI + SQLAlchemy async** — matches the async httpx scraper and keeps the stack consistent
- **Next.js 15 App Router + Tailwind** — standard for a public-facing service, good for future SSR/SEO if needed
- **APScheduler inside FastAPI** — avoids a separate Celery/Redis stack for a single weekly job
- **YGOPRODECK JSON API for tournament listing** — the `/tournaments/` page uses DataTables with AJAX; the underlying endpoint is `ygoprodeck.com/api/tournament/getTournaments.php` which returns clean JSON directly
- **Deck card parsing via DOM `[data-card][data-cardname]`** — deck pages render cards as HTML elements with data attributes; zone (main/extra/side) is inferred by walking up the DOM to the section container

## Stack

| Layer | Choice |
|---|---|
| Scraper | Python 3.12, httpx (async), BeautifulSoup4 + lxml |
| API | FastAPI, SQLAlchemy (async), Alembic, Pydantic |
| Database | PostgreSQL 16 |
| Scheduler | APScheduler (cron: Sundays 03:00 UTC) |
| Frontend | Next.js 15 App Router, TypeScript, Tailwind CSS |
| Dev infra | Docker Compose (db + backend + frontend) |

## Open Questions

- **Local card storage** — autocomplete currently live-proxies to `db.ygoprodeck.com` and card images load from their CDN. This violates their self-hosting terms. Tracked in [xsaardo/ygo-meta-check#1](https://github.com/xsaardo/ygo-meta-check/issues/1).
- **Price tracking** — future feature; store card prices alongside meta appearances. Not scoped yet.
- **Placement ranking** — currently stored as raw strings ("Winner", "Top 8", "Unknown"). Normalizing to numeric rank would enable sorting by finish quality.

## Next Steps

- Resolve issue #1 (local card storage + self-hosted images)
- Add `pg_trgm` for ranked autocomplete (prefix matches above mid-word matches)
- Add price tracking data model
