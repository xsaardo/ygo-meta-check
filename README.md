# YGO Meta Check

Search for a Yu-Gi-Oh! card and see if it has appeared in any tournament decklist in the past 3 months. Results link back to the specific tournament and deck on ygoprodeck.com.

Built for checking a card's competitive value quickly — useful at a card shop before buying or selling.

## Stack

- **Frontend** — Next.js 15 (App Router), TypeScript, Tailwind CSS
- **Backend** — FastAPI, SQLAlchemy (async), Alembic
- **Database** — PostgreSQL 16
- **Scraper** — httpx + BeautifulSoup4, runs weekly via APScheduler

## How it works

A weekly scraper pulls tournament results from ygoprodeck.com, fetches each submitted decklist, and stores every card by name, zone (main/extra/side), and quantity. When you search a card, the app queries that local database and shows every tournament appearance in the lookback window.

## Running locally

**Prerequisites:** Docker, Docker Compose

```bash
# Clone and start all services
git clone https://github.com/xsaardo/ygo-meta-check.git
cd ygo-meta-check
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

The database starts empty. Trigger an initial scrape:

```bash
curl -X POST http://localhost:8000/api/scrape/trigger
```

This takes a few minutes depending on how many tournaments have submitted decklists. After it completes, search any card name in the UI.

## Environment variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `ygo_secret` | Database password |
| `SCRAPER_MONTHS_LOOKBACK` | `3` | How many months back to scrape |
| `SCRAPER_WORKERS` | `5` | Concurrent deck fetch workers |
| `SCRAPER_DELAY_SECONDS` | `1.5` | Delay between requests |
| `ALLOW_MANUAL_SCRAPE` | `true` | Enable the `/api/scrape/trigger` endpoint |

## Scraper schedule

The scraper runs automatically every Sunday at 03:00 UTC. It only fetches tournaments and decks not already in the database, so incremental runs are fast.

## API

| Endpoint | Description |
|---|---|
| `GET /api/search?card=<name>&months=3&zone=<main\|extra\|side>` | Search card tournament appearances |
| `GET /api/autocomplete?q=<query>` | Card name suggestions |
| `POST /api/scrape/trigger` | Trigger a manual scrape |
| `GET /api/scrape/status` | Check if a scrape is running |

## Known limitations / roadmap

- Card autocomplete currently proxies live to the YGOPRODECK API — local card storage is planned ([#1](https://github.com/xsaardo/ygo-meta-check/issues/1))
- Card images are loaded from the YGOPRODECK CDN — will be self-hosted alongside #1
- Price tracking is a planned future feature
