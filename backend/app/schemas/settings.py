from typing import Optional, Dict, List
from pydantic import BaseModel


class SettingsResponse(BaseModel):
    pipedrive_api_token: Optional[str] = None
    pipedrive_pipeline_id: Optional[int] = None
    pipedrive_stage_id: Optional[int] = None
    scraping_enabled: bool = True
    headless_browser: bool = True
    scraper_timeout_seconds: int = 30
    scraper_max_retries: int = 3
    scraper_min_delay_seconds: float = 2.0
    scraper_max_delay_seconds: float = 6.0
    screenshot_on_error: bool = True
    html_snapshot_on_error: bool = True


class SettingsUpdate(BaseModel):
    pipedrive_api_token: Optional[str] = None
    pipedrive_pipeline_id: Optional[int] = None
    pipedrive_stage_id: Optional[int] = None
    scraping_enabled: Optional[bool] = None
    headless_browser: Optional[bool] = None
    scraper_timeout_seconds: Optional[int] = None
    scraper_max_retries: Optional[int] = None
    scraper_min_delay_seconds: Optional[float] = None
    scraper_max_delay_seconds: Optional[float] = None
    screenshot_on_error: Optional[bool] = None
    html_snapshot_on_error: Optional[bool] = None
