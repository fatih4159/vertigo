import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import Enum as SAEnum
from app.core.database import Base


class JobStatus(str, enum.Enum):
    NEW = "new"
    VALIDATED = "validated"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"
    DEAL_CREATED = "deal_created"
    FAILED = "failed"


class WorkModel(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"
    UNKNOWN = "unknown"


class JobBoard(str, enum.Enum):
    LINKEDIN = "linkedin"
    STEPSTONE = "stepstone"
    INDEED = "indeed"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WELLFOUND = "wellfound"
    COMPANY = "company"
    UNKNOWN = "unknown"


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    company_website: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    job_title: Mapped[str] = mapped_column(String(500), nullable=False)
    job_board: Mapped[JobBoard] = mapped_column(SAEnum(JobBoard), nullable=False, index=True)
    job_url: Mapped[str] = mapped_column(String(2000), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    work_model: Mapped[WorkModel] = mapped_column(
        SAEnum(WorkModel), default=WorkModel.UNKNOWN, nullable=False
    )
    tech_stack: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus), default=JobStatus.NEW, nullable=False, index=True
    )
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    search_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
