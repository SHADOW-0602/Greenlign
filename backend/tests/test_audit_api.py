"""Tests for Audit REST API endpoints."""

import time
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
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.disclosure import Disclosure
from app.models.emission_factor import EmissionFactor
from app.models.source_document import SourceDocument


@pytest.fixture
async def seeded_provenance_data(
    db_session: AsyncSession,
) -> tuple[SourceDocument, ActivityData, EmissionFactor, Calculation]:
    """Create a linked provenance chain in database."""
    entity_id = uuid.uuid4()

    doc = SourceDocument(
        id=uuid.uuid4(),
        entity_id=entity_id,
        filename="invoice_march.csv",
        file_type="csv",
        file_size_bytes=2048,
        file_hash_sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abc",
        storage_path="documents/test/invoice.csv",
        status="completed",
    )
    db_session.add(doc)

    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        source_document_id=doc.id,
        raw_line_ref="row:12",
        activity_type="electricity_purchase",
        quantity=Decimal("1000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_TEST",
        scope=2,
        ghg_category="Purchased Electricity",
        classification_confidence=0.98,
        status="computed",
    )
    db_session.add(act)

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

    calc = Calculation(
        id=uuid.uuid4(),
        activity_data_id=act.id,
        emission_factor_id=factor.id,
        formula_applied="1000 kWh * 0.3859 kgCO2e/kWh / 1000 = 0.38590000 tCO2e",
        result_tco2e=Decimal("0.38590000"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc)

    audit_entry = AuditLogEntry(
        id=uuid.uuid4(),
        entity_type="activity_data",
        entity_id=act.id,
        action="CALCULATE",
        actor="test_user",
        detail={"result_tco2e": "0.38590000"},
    )
    db_session.add(audit_entry)

    await db_session.commit()
    return doc, act, factor, calc


@pytest.mark.asyncio
async def test_get_trace_endpoint_performance_and_content(
    db_session: AsyncSession,
    seeded_provenance_data: tuple[SourceDocument, ActivityData, EmissionFactor, Calculation],
) -> None:
    """GET /api/audit/trace/{calc_id} returns full chain in < 200ms."""
    doc, act, factor, calc = seeded_provenance_data

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            start_time = time.perf_counter()
            resp = await ac.get(f"/api/audit/trace/{calc.id}")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert resp.status_code == 200
            # Target latency under 200ms
            assert elapsed_ms < 200.0, f"Expected <200ms, took {elapsed_ms:.2f}ms"

            data = resp.json()
            assert data["calculation"]["id"] == str(calc.id)
            assert data["calculation"]["result_tco2e"] == "0.38590000"
            assert data["activity"]["id"] == str(act.id)
            assert data["activity"]["supplier_ref"] == "TOKEN_SUPP_TEST"
            assert data["source_document"]["filename"] == "invoice_march.csv"
            assert data["source_document"]["file_hash_sha256"] == doc.file_hash_sha256
            assert Decimal(data["emission_factor"]["factor_value"]) == Decimal("0.3859")
            assert len(data["audit_events"]) >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_trace_not_found(db_session: AsyncSession) -> None:
    """GET /api/audit/trace/{unknown_id} returns 404."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(f"/api/audit/trace/{uuid.uuid4()}")
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_audit_logs_query_endpoint(
    db_session: AsyncSession,
    seeded_provenance_data: tuple[SourceDocument, ActivityData, EmissionFactor, Calculation],
) -> None:
    """GET /api/audit/logs returns filterable audit entries."""
    _, act, _, _ = seeded_provenance_data

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/audit/logs?action=CALCULATE")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) >= 1
            assert data[0]["action"] == "CALCULATE"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_guarded_calculation_delete_endpoints(
    db_session: AsyncSession,
    seeded_provenance_data: tuple[SourceDocument, ActivityData, EmissionFactor, Calculation],
) -> None:
    """DELETE /api/audit/calculations/{id} is blocked when referenced in disclosure."""
    _, _, _, calc = seeded_provenance_data

    disclosure = Disclosure(
        id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        framework="CA_SB253",
        reporting_period="2025",
        status="draft",
        line_item_refs=[calc.id],
    )
    db_session.add(disclosure)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Check endpoint
            check_resp = await ac.get(f"/api/audit/check-calculation-deletable/{calc.id}")
            assert check_resp.status_code == 200
            assert check_resp.json()["can_delete"] is False

            # Delete blocked with 409
            del_resp = await ac.delete(f"/api/audit/calculations/{calc.id}")
            assert del_resp.status_code == 409
            assert "cannot be deleted" in del_resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
