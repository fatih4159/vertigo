import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.log_entry import LogLevel


class LogEntryResponse(BaseModel):
    id: uuid.UUID
    level: LogLevel
    message: str
    source: Optional[str] = None
    extra_data: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogFilter(BaseModel):
    level: Optional[LogLevel] = None
    source: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 50


class LogListResponse(BaseModel):
    items: List[LogEntryResponse]
    total: int
    page: int
    page_size: int
