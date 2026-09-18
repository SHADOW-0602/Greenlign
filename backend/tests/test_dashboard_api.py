"""API tests for the /api/dashboard router."""

import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor


@pytest.mark.asyncio
async def test_get_dashboard_summary_api(db_session: AsyncSession) -> None:
    """Verify GET /api/dashboard/summary returns 200 with structured ESG metrics."""
    entity_id = uuid.uuid4()
    source_doc_id = uuid.uuid4()

    # 1. Seed factor
    factor = EmissionFactor(
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="electricity_purchase",
        geography="US",
        unit="kWh",
        factor_value=Decimal("0.4"),
        factor_unit="kgCO2e/kWh",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add(factor)
    await db_session.flush()

    # 2. Seed activity
    act = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="line_1",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("50000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 6, 1),
        period_end=date(2025, 6, 30),
        supplier_ref="SUPP_POWER",
        scope=2,
        ghg_category="Scope 2.1 Purchased Electricity",
        classification_confidence=0.99,
        status="calculated",
    )
    db_session.add(act)
    await db_session.flush()

    # 3. Seed calculation
    calc = Calculation(
        activity_data_id=act.id,
        emission_factor_id=factor.id,
        formula_applied="50000 kWh * 0.4 kgCO2e/kWh",
        result_tco2e=Decimal("20.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc)
    await db_session.commit()

    # 4. Query endpoint with DB session override
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/dashboard/summary?entity_id={entity_id}&reporting_period=2025"
            )
            assert resp.status_code == 200
            data = resp.json()

            assert data["entity_id"] == str(entity_id)
            assert data["reporting_period"] == "2025"
            assert data["gross_emissions_tco2e"] == pytest.approx(20.0)
            assert data["total_calculations"] == 1

            scopes = {s["scope"]: s for s in data["scope_breakdown"]}
            assert scopes[2]["total_tco2e"] == pytest.approx(20.0)
            assert scopes[2]["share_percentage"] == 100.0

            assert len(data["top_hotspots"]) == 1
            assert data["top_hotspots"][0]["ghg_category"] == "Scope 2.1 Purchased Electricity"
    finally:
        app.dependency_overrides.clear()
