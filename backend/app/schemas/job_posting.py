import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from app.models.job_posting import JobStatus, WorkModel, JobBoard


class JobPostingBase(BaseModel):
    company_name: str
    company_website: Optional[str] = None
    job_title: str
    job_board: JobBoard
    job_url: str
    description: Optional[str] = None
    location: Optional[str] = None
    work_model: WorkModel = WorkModel.UNKNOWN
    tech_stack: Optional[List[str]] = None
    score: int = 0


class JobPostingCreate(JobPostingBase):
    pass


class JobPostingUpdate(BaseModel):
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    work_model: Optional[WorkModel] = None
    tech_stack: Optional[List[str]] = None
    score: Optional[int] = None
    status: Optional[JobStatus] = None


class JobPostingResponse(JobPostingBase):
    id: uuid.UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobPostingListResponse(BaseModel):
    items: List[JobPostingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobPostingFilter(BaseModel):
    status: Optional[JobStatus] = None
    job_board: Optional[JobBoard] = None
    work_model: Optional[WorkModel] = None
    tech_stack: Optional[str] = None
    location: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20
