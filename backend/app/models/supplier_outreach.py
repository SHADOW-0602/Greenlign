import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, new_uuid


class SupplierOutreach(Base):
    __tablename__ = "supplier_outreach"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    supplier_ref: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    supplier_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    supplier_email: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    contact_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    activity_type: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    reporting_period: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT", index=True
    )
    template_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    generated_email_subject: Mapped[str] = mapped_column(
        String(512), nullable=False
    )
    generated_email_body: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    response_data_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
