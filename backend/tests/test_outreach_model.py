"""Tests for SupplierOutreach database model."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier_outreach import SupplierOutreach


@pytest.mark.asyncio
async def test_supplier_outreach_model_creation(db_session: AsyncSession) -> None:
    """Test creating and persisting a SupplierOutreach record in PostgreSQL/SQLite."""
    outreach = SupplierOutreach(
        entity_id=uuid.uuid4(),
        supplier_ref="SUPP_1029",
        supplier_name="Acme Packaging Corp",
        supplier_email="esg@acmepackaging.com",
        contact_name="Jane Doe",
        activity_type="purchased_goods_packaging",
        reporting_period="2025",
        status="DRAFT",
        template_type="PRIMARY_EMISSION_FACTOR",
        generated_email_subject="Request for FY2025 Primary Emission Factors - Acme Packaging",
        generated_email_body="Dear Jane,\n\nPlease provide your emission intensity data.",
        response_data_json={},
    )

    db_session.add(outreach)
    await db_session.commit()
    await db_session.refresh(outreach)

    assert outreach.id is not None
    assert outreach.supplier_ref == "SUPP_1029"
    assert outreach.status == "DRAFT"
    assert outreach.created_at is not None
    assert outreach.sent_at is None
    assert outreach.response_data_json == {}

    # Query back
    stmt = select(SupplierOutreach).where(SupplierOutreach.id == outreach.id)
    result = await db_session.execute(stmt)
    fetched = result.scalar_one()

    assert fetched.supplier_name == "Acme Packaging Corp"
    assert fetched.template_type == "PRIMARY_EMISSION_FACTOR"


@pytest.mark.asyncio
async def test_supplier_outreach_status_update(db_session: AsyncSession) -> None:
    """Test updating outreach status, timestamps, and response JSON."""
    outreach = SupplierOutreach(
        entity_id=uuid.uuid4(),
        supplier_ref="SUPP_2044",
        supplier_email="logistics@fastfreight.com",
        contact_name="Mark Smith",
        activity_type="freight_road_diesel",
        reporting_period="2025",
        status="SENT",
        template_type="ACTIVITY_DATA_VERIFICATION",
        generated_email_subject="Freight Verification",
        generated_email_body="Verify tonne-km",
        sent_at=datetime.now(UTC),
    )

    db_session.add(outreach)
    await db_session.commit()

    # Supplier responds
    outreach.status = "RECEIVED"
    outreach.responded_at = datetime.now(UTC)
    outreach.response_data_json = {
        "primary_factor_value": "0.142",
        "primary_factor_unit": "kgCO2e/t-km",
        "verified_by": "Mark Smith",
    }
    await db_session.commit()
    await db_session.refresh(outreach)

    assert outreach.status == "RECEIVED"
    assert outreach.responded_at is not None
    assert outreach.response_data_json["primary_factor_value"] == "0.142"
