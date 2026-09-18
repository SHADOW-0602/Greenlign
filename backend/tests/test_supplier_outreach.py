"""Unit tests for Scope 3 Supplier Outreach Agent."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.schemas.outreach import (
    CreateOutreachRequest,
    GenerateEmailRequest,
    RecordSupplierResponseRequest,
)
from app.services.supplier_outreach import SupplierOutreachService


@pytest.mark.asyncio
async def test_generate_email_heuristic_and_llm(db_session: AsyncSession) -> None:
    """Verify email generation produces appropriate subject and body (via LLM or fallback)."""
    service = SupplierOutreachService(db_session)

    req = GenerateEmailRequest(
        supplier_name="Global Freight Logistics",
        supplier_ref="SUPP_FREIGHT_99",
        activity_type="freight_road_diesel",
        reporting_period="2025",
        template_type="PRIMARY_EMISSION_FACTOR",
    )

    resp = await service.generate_email(req)
    assert resp.template_type == "PRIMARY_EMISSION_FACTOR"
    assert "Global Freight Logistics" in resp.subject or "Global Freight Logistics" in resp.body
    assert "2025" in resp.subject or "2025" in resp.body
    assert len(resp.body) > 50


@pytest.mark.asyncio
async def test_find_missing_scope3_suppliers(db_session: AsyncSession) -> None:
    """Verify detection of Scope 3 suppliers needing primary data."""
    entity_id = uuid.uuid4()
    source_doc_id = uuid.uuid4()

    # Create an emission factor with generic proxy source
    factor = EmissionFactor(
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="purchased_goods",
        geography="US",
        unit="USD",
        factor_value=Decimal("0.25"),
        factor_unit="kgCO2e/USD",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add(factor)
    await db_session.flush()

    # Scope 3 supplier activity
    act = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="row_10",
        entity_id=entity_id,
        activity_type="purchased_goods",
        quantity=Decimal("100000"),
        unit="USD",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_STEEL_44",
        scope=3,
        ghg_category="Scope 3.1 Purchased Goods",
        status="calculated",
    )
    db_session.add(act)
    await db_session.flush()

    calc = Calculation(
        activity_data_id=act.id,
        emission_factor_id=factor.id,
        formula_applied="100000 * 0.25",
        result_tco2e=Decimal("25.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc)
    await db_session.commit()

    service = SupplierOutreachService(db_session)
    missing = await service.find_missing_scope3_suppliers(
        entity_id=entity_id, reporting_period="2025"
    )

    assert len(missing) == 1
    assert missing[0].supplier_ref == "SUPP_STEEL_44"
    assert missing[0].activity_type == "purchased_goods"
    assert missing[0].estimated_tco2e == pytest.approx(25.0)


@pytest.mark.asyncio
async def test_create_and_record_response_outreach(db_session: AsyncSession) -> None:
    """Verify creating outreach campaign, dispatching, and recording primary response."""
    entity_id = uuid.uuid4()
    service = SupplierOutreachService(db_session)

    # 1. Create outreach
    create_req = CreateOutreachRequest(
        entity_id=entity_id,
        supplier_ref="SUPP_BOX_12",
        supplier_name="Packaging Pros Inc",
        supplier_email="esg@packagingpros.com",
        contact_name="Sarah Miller",
        activity_type="packaging_cardboard",
        reporting_period="2025",
        template_type="PRIMARY_EMISSION_FACTOR",
        custom_subject="Custom Subject for FY2025",
        custom_body="Dear Sarah, please send factor.",
    )

    outreach = await service.create_outreach(create_req)
    assert outreach.id is not None
    assert outreach.status == "DRAFT"
    assert outreach.generated_email_subject == "Custom Subject for FY2025"

    # 2. Dispatch / mark SENT
    outreach = await service.send_outreach(outreach.id)
    assert outreach.status == "SENT"
    assert outreach.sent_at is not None

    # 3. Record response
    resp_req = RecordSupplierResponseRequest(
        primary_factor_value=0.18,
        primary_factor_unit="kgCO2e/kg",
        verified_quantity=5000.0,
        response_notes="Supplier provided certified ISO 14064 LCA factor.",
    )
    updated = await service.record_response(outreach.id, resp_req)
    assert updated.status == "RECEIVED"
    assert updated.responded_at is not None
    assert updated.response_data_json["primary_factor_value"] == 0.18
    assert updated.response_data_json["primary_factor_unit"] == "kgCO2e/kg"
