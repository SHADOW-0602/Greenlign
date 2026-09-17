"""Tests for Disclosures REST API endpoints."""

import io
import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest
from httpx import ASGITransport
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor


@pytest.fixture
async def setup_entity_data(
    db_session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create sample calculations for an entity."""
    entity_id = uuid.uuid4()

    factor = EmissionFactor(
        id=uuid.uuid4(),
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="electricity_purchase",
        geography="US",
        unit="kWh",
        factor_value=Decimal("0.3859"),
        factor_unit="kgCO2e/kWh",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add(factor)

    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        raw_line_ref="row:1",
        activity_type="electricity_purchase",
        quantity=Decimal("1000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_TEST",
        scope=2,
        ghg_category="Purchased Electricity",
        status="computed",
    )
    db_session.add(act)

    calc = Calculation(
        id=uuid.uuid4(),
        activity_data_id=act.id,
        emission_factor_id=factor.id,
        formula_applied="1000 kWh * 0.3859 = 0.38590000 tCO2e",
        result_tco2e=Decimal("0.38590000"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc)
    await db_session.commit()
    return entity_id, calc.id


@pytest.mark.asyncio
async def test_check_eligibility_endpoint() -> None:
    """POST /api/disclosures/check-eligibility returns multi-framework status."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "annual_revenue_usd": "1200000000",
            "does_business_in_california": True,
        }
        resp = await ac.post("/api/disclosures/check-eligibility", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["frameworks"]["CA_SB253"]["is_eligible"] is True
        assert data["frameworks"]["GHG_PROTOCOL"]["is_eligible"] is True


@pytest.mark.asyncio
async def test_generate_disclosure_and_download_pdf(
    db_session: AsyncSession,
    setup_entity_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """POST /api/disclosures/generate creates disclosure, and GET download-pdf returns PDF."""
    entity_id, calc_id = setup_entity_data

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            gen_payload = {
                "entity_id": str(entity_id),
                "framework": "CA_SB253",
                "reporting_period": "2025",
                "entity_profile": {
                    "annual_revenue_usd": "1500000000",
                    "does_business_in_california": True,
                },
            }
            resp = await ac.post("/api/disclosures/generate", json=gen_payload)
            assert resp.status_code == 201
            data = resp.json()
            assert data["framework"] == "CA_SB253"
            assert data["total_tco2e"] == "0.38590000"
            assert str(calc_id) in [str(c) for c in data["line_item_refs"]]
            disc_id = data["id"]

            # Download PDF
            pdf_resp = await ac.get(f"/api/disclosures/{disc_id}/download-pdf")
            assert pdf_resp.status_code == 200
            assert pdf_resp.headers["content-type"] == "application/pdf"
            assert len(pdf_resp.content) > 500

            # Verify PDF is readable
            reader = PdfReader(io.BytesIO(pdf_resp.content))
            assert len(reader.pages) >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_disclosure_ineligible_blocked(
    db_session: AsyncSession,
    setup_entity_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """POST /api/disclosures/generate returns 403 Forbidden when entity is ineligible."""
    entity_id, _ = setup_entity_data

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            gen_payload = {
                "entity_id": str(entity_id),
                "framework": "CA_SB253",
                "reporting_period": "2025",
                "entity_profile": {
                    "annual_revenue_usd": "500000000",
                    "does_business_in_california": False,
                },
            }
            resp = await ac.post("/api/disclosures/generate", json=gen_payload)
            assert resp.status_code == 403
            assert "not eligible" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
