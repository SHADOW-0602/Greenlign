"""Unit tests for Anomaly Detection API endpoints."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.anomaly_flag import AnomalyFlag
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor


@pytest.mark.asyncio
async def test_scan_anomalies_endpoint(db_session: AsyncSession) -> None:
    """POST /api/anomalies/scan should execute scan and return summary."""
    entity_id = uuid.uuid4()

    # Create baseline and current records
    factor = EmissionFactor(
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="natural_gas_combustion",
        geography="US",
        unit="therms",
        factor_value=Decimal("0.0053"),
        factor_unit="tCO2e/therm",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add(factor)
    await db_session.flush()

    # 2024 baseline: 1,000 therms -> 5.3 tCO2e
    act_2024 = ActivityData(
        raw_line_ref="row:1",
        entity_id=entity_id,
        activity_type="natural_gas_combustion",
        quantity=Decimal("1000"),
        unit="therms",
        geography="US",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        supplier_ref="TOKEN_SUPP_GAS",
        scope=1,
        status="calculated",
    )
    db_session.add(act_2024)
    await db_session.flush()
    calc_2024 = Calculation(
        activity_data_id=act_2024.id,
        emission_factor_id=factor.id,
        formula_applied="qty * factor",
        result_tco2e=Decimal("5.3"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_2024)

    # 2025 current: 950 therms, emissions reported as 0.5 tCO2e (90% drop)
    act_2025 = ActivityData(
        raw_line_ref="row:2",
        entity_id=entity_id,
        activity_type="natural_gas_combustion",
        quantity=Decimal("950"),
        unit="therms",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="TOKEN_SUPP_GAS",
        scope=1,
        status="calculated",
    )
    db_session.add(act_2025)
    await db_session.flush()
    calc_2025 = Calculation(
        activity_data_id=act_2025.id,
        emission_factor_id=factor.id,
        formula_applied="qty * factor",
        result_tco2e=Decimal("0.5"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_2025)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/anomalies/scan",
                json={
                    "entity_id": str(entity_id),
                    "current_period": "2025",
                    "baseline_period": "2024",
                    "yoy_threshold_pct": 50.0,
                    "zscore_threshold": 3.0,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["entity_id"] == str(entity_id)
            assert data["flags_detected_count"] >= 1
            assert len(data["flags"]) >= 1
            assert data["flags"][0]["flag_type"] == "YOY_DROP"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_list_and_resolve_anomaly_endpoint(db_session: AsyncSession) -> None:
    """GET and PATCH /api/anomalies should list and resolve flags."""
    entity_id = uuid.uuid4()
    flag = AnomalyFlag(
        entity_id=entity_id,
        reporting_period="2025",
        flag_type="INTENSITY_OUTLIER",
        severity="WARNING",
        title="Outlier in freight intensity",
        description="High intensity detected in freight line item.",
        status="OPEN",
        details_json={"z_score": 3.4},
    )
    db_session.add(flag)
    await db_session.commit()
    await db_session.refresh(flag)

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. List anomalies
            res = await client.get(f"/api/anomalies?entity_id={entity_id}&status=OPEN")
            assert res.status_code == 200
            flags = res.json()
            assert len(flags) >= 1
            assert flags[0]["id"] == str(flag.id)

            # 2. Resolve anomaly (confirm)
            patch_res = await client.patch(
                f"/api/anomalies/{flag.id}/resolve",
                json={
                    "status": "CONFIRMED",
                    "notes": "Verified data entry typo with carrier logistics invoice.",
                    "actor": "auditor_bob",
                },
            )
            assert patch_res.status_code == 200
            updated = patch_res.json()
            assert updated["status"] == "CONFIRMED"
            assert updated["resolved_by"] == "auditor_bob"
            assert updated["resolution_notes"] is not None
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_check_narrative_endpoint(db_session: AsyncSession) -> None:
    """POST /api/anomalies/check-narrative should evaluate text and return findings."""
    entity_id = uuid.uuid4()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/anomalies/check-narrative",
                json={
                    "entity_id": str(entity_id),
                    "reporting_period": "2025",
                    "baseline_period": "2024",
                    "narrative_text": (
                        "Through our solar power transition, we cut emissions by 60% in 2025."
                    ),
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert "overall_status" in data
            assert "findings" in data
    finally:
        app.dependency_overrides.pop(get_db, None)
