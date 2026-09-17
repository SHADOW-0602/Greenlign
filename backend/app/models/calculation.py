import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, new_uuid


class Calculation(Base):
    __tablename__ = "calculation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    activity_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_data.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    emission_factor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emission_factor.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    formula_applied: Mapped[str] = mapped_column(Text, nullable=False)
    result_tco2e: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    computed_by: Mapped[str] = mapped_column(
        String(64), nullable=False, default="calc_engine_v1"
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
