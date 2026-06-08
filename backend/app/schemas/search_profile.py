import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SearchProfileBase(BaseModel):
    name: str
    keywords: List[str]
    locations: Optional[List[str]] = None
    sources: List[str]
    schedule_minutes: int = 60
    active: bool = True
    remote_only: bool = False


class SearchProfileCreate(SearchProfileBase):
    pass


class SearchProfileUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    schedule_minutes: Optional[int] = None
    active: Optional[bool] = None
    remote_only: Optional[bool] = None


class SearchProfileResponse(SearchProfileBase):
    id: uuid.UUID
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
