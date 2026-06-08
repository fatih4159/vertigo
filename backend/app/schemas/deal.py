import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.deal import DealStatus


class DealBase(BaseModel):
    job_id: uuid.UUID
    pipedrive_deal_id: Optional[int] = None
    pipedrive_org_id: Optional[int] = None
    status: DealStatus = DealStatus.PENDING


class DealCreate(DealBase):
    pass


class DealResponse(DealBase):
    id: uuid.UUID
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealWithJobResponse(DealResponse):
    job_company: Optional[str] = None
    job_title: Optional[str] = None
    job_board: Optional[str] = None
