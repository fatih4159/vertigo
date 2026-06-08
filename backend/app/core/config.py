from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "Cynefa DaaS Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    JWT_SECRET: str = "changeme-in-production-use-a-strong-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "cynefa_db"
    POSTGRES_USER: str = "cynefa"
    POSTGRES_PASSWORD: str = "cynefa_password"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_URL: str = "redis://redis:6379/0"

    PIPEDRIVE_API_TOKEN: Optional[str] = None
    PIPEDRIVE_PIPELINE_ID: Optional[int] = None
    PIPEDRIVE_STAGE_ID: Optional[int] = None
    PIPEDRIVE_BASE_URL: str = "https://api.pipedrive.com/v1"

    SCRAPING_ENABLED: bool = True
    HEADLESS_BROWSER: bool = True
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    SCRAPER_TIMEOUT_SECONDS: int = 30
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_MIN_DELAY_SECONDS: float = 2.0
    SCRAPER_MAX_DELAY_SECONDS: float = 6.0
    SCREENSHOT_ON_ERROR: bool = True
    HTML_SNAPSHOT_ON_ERROR: bool = True
    SCREENSHOT_DIR: str = "/tmp/cynefa_screenshots"

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://frontend:3000"]

    DEFAULT_SEARCH_KEYWORDS: List[str] = [
        "Software Engineer",
        "Software Developer",
        "Backend Developer",
        "Frontend Developer",
        "Fullstack Developer",
        "React Developer",
        "Angular Developer",
        "Node.js Developer",
        "Java Developer",
        "Python Developer",
        ".NET Developer",
        "PHP Developer",
        "Laravel Developer",
        "Symfony Developer",
        "Mobile Developer",
        "Android Developer",
        "iOS Developer",
        "DevOps Engineer",
        "Platform Engineer",
        "Cloud Engineer",
    ]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
