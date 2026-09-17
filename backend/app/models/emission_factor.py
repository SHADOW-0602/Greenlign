import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, new_uuid


class EmissionFactor(Base):
    __tablename__ = "emission_factor"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    geography: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    factor_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    published_date: Mapped[date] = mapped_column(nullable=False)
    effective_from: Mapped[date] = mapped_column(nullable=False, index=True)
    effective_to: Mapped[date | None] = mapped_column(nullable=True)
