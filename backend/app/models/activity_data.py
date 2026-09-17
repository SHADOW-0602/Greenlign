import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, new_uuid


class ActivityData(Base):
    __tablename__ = "activity_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    raw_line_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    activity_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    geography: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    supplier_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[int | None] = mapped_column(nullable=True)
    ghg_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_review", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
