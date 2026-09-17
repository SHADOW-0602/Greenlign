"""Tests for calculation REST API endpoints."""

import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.emission_factor import EmissionFactor


@pytest.fixture
async def seeded_factor_and_activity(
    db_session: AsyncSession,
) -> tuple[EmissionFactor, ActivityData]:
    """Create a matching factor and activity in the test database."""
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
        effective_to=None,
    )
    db_session.add(factor)

    activity = ActivityData(
        id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        raw_line_ref="row:1",
        activity_type="electricity_purchase",
        quantity=Decimal("1000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_TEST",
        status="classified",
    )
    db_session.add(activity)
    await db_session.commit()
    return factor, activity


@pytest.mark.asyncio
async def test_compute_single_activity_endpoint(
    db_session: AsyncSession,
    seeded_factor_and_activity: tuple[EmissionFactor, ActivityData],
) -> None:
    """POST /api/calculations/compute/{activity_id} returns 200 with Calculation details."""
    _, activity = seeded_factor_and_activity

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(f"/api/calculations/compute/{activity.id}")

            assert resp.status_code == 200
            data = resp.json()
            assert data["activity_data_id"] == str(activity.id)
            assert data["result_tco2e"] == "0.38590000"
            assert "formula_applied" in data
            calc_id = data["id"]

            # Test GET /api/calculations/{id}
            get_resp = await ac.get(f"/api/calculations/{calc_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == calc_id

            # Test GET /api/calculations/by-activity/{activity_id}
            by_act_resp = await ac.get(f"/api/calculations/by-activity/{activity.id}")
            assert by_act_resp.status_code == 200
            assert by_act_resp.json()["id"] == calc_id
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_compute_single_activity_not_found(
    db_session: AsyncSession,
) -> None:
    """POST /api/calculations/compute/{non_existent} returns 404."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(f"/api/calculations/compute/{uuid.uuid4()}")
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_batch_compute_endpoint(
    db_session: AsyncSession,
    seeded_factor_and_activity: tuple[EmissionFactor, ActivityData],
) -> None:
    """POST /api/calculations/batch-compute computes list of activity IDs."""
    _, activity = seeded_factor_and_activity

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {"activity_ids": [str(activity.id)]}
            resp = await ac.post("/api/calculations/batch-compute", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["computed_count"] == 1
            assert data["pending_factor_count"] == 0
            assert len(data["calculations"]) == 1
            assert data["calculations"][0]["result_tco2e"] == "0.38590000"
    finally:
        app.dependency_overrides.clear()
