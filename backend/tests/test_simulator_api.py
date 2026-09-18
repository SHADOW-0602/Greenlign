"""API tests for the /api/simulator router."""

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
async def test_get_simulator_levers_api(db_session: AsyncSession) -> None:
    """Verify GET /api/simulator/levers returns list of available levers."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/simulator/levers")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) >= 4
            lever_ids = [item["lever_id"] for item in data]
            assert "SOLAR_PPA_GRID_ELEC" in lever_ids
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_simulate_api(db_session: AsyncSession) -> None:
    """Verify POST /api/simulator/simulate runs scenario calculation."""
    entity_id = uuid.uuid4()
    source_doc_id = uuid.uuid4()

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

    act = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="line_1",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("100000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_POWER",
        scope=2,
        ghg_category="Scope 2.1 Purchased Electricity",
        status="calculated",
    )
    db_session.add(act)
    await db_session.flush()

    calc = Calculation(
        activity_data_id=act.id,
        emission_factor_id=factor.id,
        formula_applied="100000 * 0.4",
        result_tco2e=Decimal("40.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "entity_id": str(entity_id),
                "reporting_period": "2025",
                "applied_levers": [
                    {
                        "lever_id": "SOLAR_PPA_GRID_ELEC",
                        "implementation_rate": 0.5,
                        "custom_capex_usd": 0.0,
                        "custom_annual_opex_delta_usd": -1500.0,
                    }
                ],
                "target_reduction_percent": 30.0,
            }
            resp = await client.post("/api/simulator/simulate", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data["entity_id"] == str(entity_id)
            assert data["baseline_gross_tco2e"] == pytest.approx(40.0)
            assert data["total_reduction_tco2e"] == pytest.approx(20.0)
            assert data["simulated_gross_tco2e"] == pytest.approx(20.0)
            assert data["total_reduction_percent"] == pytest.approx(50.0)
            assert data["target_met"] is True
            assert len(data["ranked_levers"]) == 1
            assert data["ranked_levers"][0]["roi_rank"] == 1
    finally:
        app.dependency_overrides.clear()
