from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ygo:ygo_secret@localhost:5432/ygo_meta"
    allow_manual_scrape: bool = True
    # Scraper settings
    scraper_workers: int = 5
    scraper_delay_seconds: float = 1.5
    scraper_months_lookback: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
