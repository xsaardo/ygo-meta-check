from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str  # required — no default; app refuses to start without DATABASE_URL set
    allow_manual_scrape: bool = False
    # Scraper settings
    scraper_workers: int = 5
    scraper_delay_seconds: float = 1.5
    scraper_months_lookback: int = 3
    # Card image storage — absolute path on the host / container filesystem
    card_images_dir: str = "/app/card_images"

    class Config:
        env_file = ".env"


settings = Settings()
