import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SAEnum
from app.core.database import Base


class DealStatus(str, enum.Enum):
    PENDING = "pending"
    CREATED = "created"
    FAILED = "failed"
    SYNCED = "synced"


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipedrive_deal_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pipedrive_org_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[DealStatus] = mapped_column(
        SAEnum(DealStatus), default=DealStatus.PENDING, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
