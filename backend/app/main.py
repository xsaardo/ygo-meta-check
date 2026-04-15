import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.autocomplete import router as autocomplete_router
from app.api.prices import router as prices_router
from app.api.scrape import router as scrape_router
from app.api.search import router as search_router
from app.config import settings
from app.scraper.scheduler import init_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YGO Meta Relevance API",
    description="Search for Yu-Gi-Oh! cards and check their tournament meta relevance.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://*.railway.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(autocomplete_router, prefix="/api", tags=["autocomplete"])
app.include_router(prices_router, prefix="/api", tags=["prices"])
app.include_router(scrape_router, prefix="/api", tags=["admin"])


@app.on_event("startup")
async def startup():
    # Ensure the card images directory exists and mount it as static files
    images_dir = Path(settings.card_images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/cards", StaticFiles(directory=str(images_dir)), name="card_images")

    init_scheduler()
    logger.info("YGO Meta API started")


@app.on_event("shutdown")
async def shutdown():
    from app.scraper.scheduler import scheduler
    scheduler.shutdown()


@app.get("/health")
async def health():
    return {"status": "ok"}
