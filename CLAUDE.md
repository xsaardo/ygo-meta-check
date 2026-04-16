# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Yu-Gi-Oh! meta relevance tracker. Scrapes tournament results from ygoprodeck.com weekly, stores decklists in PostgreSQL, and lets users search how often a card appears across recent tournaments.

## Commands

### Docker (local dev)

```bash
docker compose up --build       # Start all services (db, backend, frontend)
```

After services are healthy, seed data:

```bash
curl -X POST http://localhost:8000/api/cards/sync     # Sync ~12k cards + images (~200MB)
curl -X POST http://localhost:8000/api/scrape/trigger # Scrape recent tournament results
```

### Backend

```bash
cd backend

# Run (outside Docker)
DATABASE_URL="postgresql+asyncpg://ygo:ygo_secret@localhost:5432/ygo_meta" \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Lint
ruff check .
ruff format --check .
ruff format .           # auto-fix

# Test
pytest -v --tb=short

# Single test
pytest tests/test_smoke.py::test_name -v

# Migrations (also run automatically on startup)
alembic upgrade head
```

### Frontend

```bash
cd frontend

npm run dev             # Dev server (localhost:3000)
npm run build           # Production build
npm run lint            # ESLint
npx tsc --noEmit        # Type check
npm test                # Vitest (one-shot)
npm test -- --watch     # Vitest (watch mode)
```

## Architecture

### Stack

- **Frontend:** Next.js 15 (App Router, SSR), TypeScript strict, Tailwind CSS, Vitest
- **Backend:** FastAPI + SQLAlchemy 2.0 async, PostgreSQL 16 (asyncpg), Alembic, APScheduler
- **Deployment:** Railway.app — backend + frontend as separate services, PostgreSQL plugin

### Data Flow

1. **Weekly scraper** (Sunday 3am UTC via APScheduler): fetches tournament results from ygoprodeck.com → parses decklists → stores card entries (zone, quantity) → downloads card images to local filesystem
2. **Search**: user types → `GET /api/autocomplete` (pg_trgm) → selects card → `GET /api/search` returns every tournament appearance with placement/player
3. **Card sync** (`POST /api/cards/sync`): pulls all cards from YGOPRODECK API + downloads images incrementally

### Key Entry Points

| File | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI app, startup/shutdown, migrations |
| `backend/app/models.py` | SQLAlchemy ORM (cards, tournaments, decks, placements, deck_cards) |
| `backend/app/api/search.py` | Core search query |
| `backend/app/scraper/runner.py` | Scraper orchestration |
| `backend/app/scraper/scheduler.py` | APScheduler config |
| `frontend/app/page.tsx` | Main search UI (SSR) |
| `frontend/app/lib/api.ts` | Frontend API client |

### Important Behaviors

- **Migrations run automatically** on backend startup (subprocess-isolated to avoid asyncio conflicts with Alembic)
- **URL validation** is enforced for both image URLs and deck URLs — only ygoprodeck.com origins are allowed. Smoke tests in `backend/tests/test_smoke.py` cover this security boundary.
- **`NEXT_PUBLIC_API_URL`** is used for browser-side requests; **`BACKEND_INTERNAL_URL`** is used for Next.js server-side rewrites (matters in production Railway config)
- **`ALLOW_MANUAL_SCRAPE`** env var gates the `POST /api/scrape/trigger` endpoint (default true in dev, should be false in prod)
- **Card images** (~200MB) are served from a mounted local volume — re-downloaded after Railway volume resets (S3 migration noted as future work)

### Environment Variables

See `.env.example`. Key ones:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | _(set by docker-compose)_ | asyncpg URL |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Browser-facing API URL |
| `BACKEND_INTERNAL_URL` | _(optional)_ | Next.js server-side rewrite target |
| `SCRAPER_MONTHS_LOOKBACK` | `3` | Tournament lookback window |
| `ALLOW_MANUAL_SCRAPE` | `true` | Enable manual scrape trigger |
| `CARD_IMAGES_DIR` | `/app/card_images` | Local image cache path |
