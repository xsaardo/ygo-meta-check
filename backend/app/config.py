from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ygo:ygo_secret@localhost:5432/ygo_meta"
    allow_manual_scrape: bool = False
    # Scraper settings
    scraper_workers: int = 5
    scraper_delay_seconds: float = 1.5
    scraper_months_lookback: int = 3
    # Card image storage — absolute path on the host / container filesystem
    card_images_dir: str = "/app/card_images"
    # Comma-separated list of allowed CORS origins (production frontend URL(s))
    allowed_origins: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
