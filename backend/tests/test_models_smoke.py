"""Smoke and unit tests: verify SQLAlchemy models can be imported, introspected, and inserted."""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from app.models import (
    ActivityData,
    AuditLogEntry,
    Base,
    Calculation,
    Disclosure,
    EmissionFactor,
)
from app.models.base import new_uuid


def test_all_models_importable():
    """All six models must import without error."""
    assert ActivityData.__tablename__ == "activity_data"
    assert EmissionFactor.__tablename__ == "emission_factor"
    assert Calculation.__tablename__ == "calculation"
    assert AuditLogEntry.__tablename__ == "audit_log"
    assert Disclosure.__tablename__ == "disclosure"


def test_base_has_all_tables():
    table_names = set(Base.metadata.tables.keys())
    assert "activity_data" in table_names
    assert "emission_factor" in table_names
    assert "calculation" in table_names
    assert "audit_log" in table_names
    assert "disclosure" in table_names


def test_new_uuid_helper():
    u1 = new_uuid()
    u2 = new_uuid()
    assert isinstance(u1, uuid.UUID)
    assert isinstance(u2, uuid.UUID)
    assert u1 != u2


def test_model_column_specifications():
    """Verify precision, scale, and types match global constraints."""
    # ActivityData.quantity is Numeric(20, 6)
    qty_col = ActivityData.__table__.c.quantity
    assert isinstance(qty_col.type, Numeric)
    assert qty_col.type.precision == 20
    assert qty_col.type.scale == 6

    # EmissionFactor.factor_value is Numeric(20, 8)
    factor_col = EmissionFactor.__table__.c.factor_value
    assert isinstance(factor_col.type, Numeric)
    assert factor_col.type.precision == 20
    assert factor_col.type.scale == 8

    # Calculation.result_tco2e is Numeric(20, 8)
    res_col = Calculation.__table__.c.result_tco2e
    assert isinstance(res_col.type, Numeric)
    assert res_col.type.precision == 20
    assert res_col.type.scale == 8

    # AuditLogEntry.detail is JSONB
    detail_col = AuditLogEntry.__table__.c.detail
    assert isinstance(detail_col.type, JSONB)

    # Disclosure.line_item_refs is ARRAY(UUID)
    refs_col = Disclosure.__table__.c.line_item_refs
    assert isinstance(refs_col.type, ARRAY)
    assert isinstance(refs_col.type.item_type, UUID)


def test_foreign_keys():
    """Verify Calculation foreign keys to ActivityData and EmissionFactor."""
    calc_table = Calculation.__table__
    fk_targets = {fk.target_fullname for fk in calc_table.foreign_keys}
    assert "activity_data.id" in fk_targets
    assert "emission_factor.id" in fk_targets


@pytest.mark.asyncio
async def test_activity_data_insert_and_read(db_session):
    row = ActivityData(
        source_document_id=None,
        raw_line_ref="row:1",
        entity_id=uuid.uuid4(),
        activity_type="electricity_purchase",
        quantity=Decimal("1000.000000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="TOKEN_ABC123",
        status="pending_review",
    )
    db_session.add(row)
    await db_session.flush()
    assert row.id is not None
    assert row.status == "pending_review"
    assert row.quantity == Decimal("1000.000000")
