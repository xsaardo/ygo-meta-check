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

Card data and images are synced weekly from the YGOPRODECK API and served locally — no per-keystroke calls to their CDN.

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

The database starts empty. Run the initial data load:

```bash
# Sync all ~12k cards and download card images (~200MB)
curl -X POST http://localhost:8000/api/cards/sync

# Scrape tournament results
curl -X POST http://localhost:8000/api/scrape/trigger
```

Both run in the background — check status with:

```bash
curl http://localhost:8000/api/cards/sync/status
curl http://localhost:8000/api/scrape/status
```

## Environment variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `ygo_secret` | Database password |
| `SCRAPER_MONTHS_LOOKBACK` | `3` | How many months back to scrape |
| `SCRAPER_WORKERS` | `5` | Concurrent deck fetch workers |
| `SCRAPER_DELAY_SECONDS` | `1.5` | Delay between requests |
| `ALLOW_MANUAL_SCRAPE` | `true` | Enable the `/api/scrape/trigger` endpoint |
| `CARD_IMAGES_DIR` | `/app/card_images` | Filesystem path for cached card images |
| `DATABASE_URL` | _(auto-set by docker-compose)_ | Async PostgreSQL URL |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL (set for production) |

## Deploying to Railway

Railway runs both services from a single repo using `railway.toml`.

### Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli): `npm install -g @railway/cli`
- A Railway account and project

### Steps

1. **Create the project and add a PostgreSQL plugin** in the Railway dashboard.

2. **Link and deploy:**

   ```bash
   railway login
   railway link
   railway up
   ```

3. **Set environment variables** in the Railway dashboard for each service:

   **Backend:**
   ```
   DATABASE_URL=<Railway PostgreSQL connection string (asyncpg)>
   ALLOW_MANUAL_SCRAPE=true
   CARD_IMAGES_DIR=/app/card_images
   ```

   **Frontend:**
   ```
   NEXT_PUBLIC_API_URL=https://<your-backend-service>.railway.app
   ```

4. **Run migrations** (Railway will run them automatically via the `startCommand` in `railway.toml`).

5. **Seed data** — after the first deploy, trigger the initial card sync and scrape:

   ```bash
   curl -X POST https://<your-backend>.railway.app/api/cards/sync
   curl -X POST https://<your-backend>.railway.app/api/scrape/trigger
   ```

> **Note:** Card images (~200MB) are written to an ephemeral volume on Railway. They persist across deploys within the same volume but will be re-downloaded after a volume reset. For long-term production use, configure an S3-compatible object store and update `_image_url()` in `autocomplete.py` to return CDN URLs.

## API

| Endpoint | Description |
|---|---|
| `GET /api/search?card=<name>&months=3&zone=<main\|extra\|side>` | Search card tournament appearances |
| `GET /api/autocomplete?q=<query>` | Card name suggestions (local DB with pg_trgm) |
| `GET /api/prices/<card_id>` | TCGPlayer + Cardmarket prices (1h cache) |
| `POST /api/scrape/trigger` | Trigger a manual tournament scrape |
| `GET /api/scrape/status` | Check if a tournament scrape is running |
| `POST /api/cards/sync` | Trigger a manual card data + image sync |
| `GET /api/cards/sync/status` | Check if a card sync is running |

## Scraper schedule

Both jobs run automatically every Sunday at 03:00 UTC (card sync at 03:30 UTC). Incremental runs only process new tournaments and decks.
