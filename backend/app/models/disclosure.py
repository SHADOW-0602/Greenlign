import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, new_uuid


class Disclosure(Base):
    __tablename__ = "disclosure"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    framework: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reporting_period: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )
    generated_document_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Array of Calculation UUIDs that feed this disclosure
    line_item_refs: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
