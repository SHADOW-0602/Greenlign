"""Unit tests for AnomalyFlag SQLAlchemy model and database roundtrip."""
import uuid
from datetime import datetime

import pytest
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models import AnomalyFlag, Base


def test_anomaly_flag_registered_in_metadata() -> None:
    """Verify AnomalyFlag table is registered in Base.metadata."""
    assert AnomalyFlag.__tablename__ == "anomaly_flag"
    assert "anomaly_flag" in Base.metadata.tables


def test_anomaly_flag_column_specifications() -> None:
    """Verify column types, nullability, and indexes on AnomalyFlag."""
    table = AnomalyFlag.__table__

    # id column
    id_col = table.c.id
    assert isinstance(id_col.type, UUID)
    assert id_col.primary_key is True

    # entity_id column
    entity_col = table.c.entity_id
    assert isinstance(entity_col.type, UUID)
    assert entity_col.nullable is False
    assert entity_col.index is True

    # reporting_period column
    period_col = table.c.reporting_period
    assert isinstance(period_col.type, String)
    assert period_col.nullable is False
    assert period_col.index is True

    # flag_type column
    flag_type_col = table.c.flag_type
    assert isinstance(flag_type_col.type, String)
    assert flag_type_col.nullable is False
    assert flag_type_col.index is True

    # severity column
    sev_col = table.c.severity
    assert isinstance(sev_col.type, String)
    assert sev_col.nullable is False

    # title and description columns
    assert isinstance(table.c.title.type, String)
    assert table.c.title.nullable is False
    assert isinstance(table.c.description.type, Text)
    assert table.c.description.nullable is False

    # status column
    status_col = table.c.status
    assert isinstance(status_col.type, String)
    assert status_col.nullable is False
    assert status_col.index is True

    # details_json column
    details_col = table.c.details_json
    assert isinstance(details_col.type, JSONB)
    assert details_col.nullable is False

    # resolution fields
    assert isinstance(table.c.resolution_notes.type, Text)
    assert table.c.resolution_notes.nullable is True
    assert isinstance(table.c.resolved_by.type, String)
    assert table.c.resolved_by.nullable is True
    assert isinstance(table.c.resolved_at.type, DateTime)
    assert table.c.resolved_at.nullable is True


@pytest.mark.asyncio
async def test_anomaly_flag_db_roundtrip(db_session) -> None:
    """Verify AnomalyFlag insertion, query, update, and resolution in PostgreSQL."""
    entity_id = uuid.uuid4()
    flag = AnomalyFlag(
        entity_id=entity_id,
        reporting_period="2025",
        flag_type="YOY_DROP",
        severity="CRITICAL",
        title="Unexplained 85% Drop in Scope 1 Emissions",
        description="Scope 1 fell from 1,200 tCO2e to 180 tCO2e without activity drop.",
        status="OPEN",
        details_json={
            "prior_tco2e": "1200.00",
            "current_tco2e": "180.00",
            "pct_change": -85.0,
            "activity_pct_change": -2.1,
        },
    )
    db_session.add(flag)
    await db_session.commit()
    await db_session.refresh(flag)

    assert flag.id is not None
    assert flag.created_at is not None
    assert flag.status == "OPEN"

    # Query back
    result = await db_session.scalars(
        select(AnomalyFlag).where(AnomalyFlag.entity_id == entity_id)
    )
    fetched = result.first()
    assert fetched is not None
    assert fetched.flag_type == "YOY_DROP"
    assert fetched.details_json["pct_change"] == -85.0

    # Resolve flag
    fetched.status = "CONFIRMED"
    fetched.resolved_by = "auditor_jane"
    fetched.resolution_notes = "Confirmed missing natural gas bill from Chicago warehouse."
    fetched.resolved_at = datetime.now()
    await db_session.commit()
    await db_session.refresh(fetched)

    assert fetched.status == "CONFIRMED"
    assert fetched.resolved_by == "auditor_jane"
