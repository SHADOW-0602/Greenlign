"""Tests for calculation service."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.services.calculation_service import CalculationService


@pytest.fixture
async def seed_test_factors(db_session: AsyncSession) -> list[EmissionFactor]:
    """Insert test factors into the test database."""
    factors = [
        EmissionFactor(
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
        ),
        EmissionFactor(
            id=uuid.uuid4(),
            source="EPA_GHG_Hub",
            source_version="2025",
            activity_type="electricity_purchase",
            geography="US-CA",
            unit="kWh",
            factor_value=Decimal("0.2154"),
            factor_unit="kgCO2e/kWh",
            published_date=date(2025, 1, 1),
            effective_from=date(2025, 1, 1),
            effective_to=None,
        ),
    ]
    for f in factors:
        db_session.add(f)
    await db_session.commit()
    return factors


@pytest.fixture
async def sample_activity(db_session: AsyncSession) -> ActivityData:
    """Create a sample classified activity."""
    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        raw_line_ref="test_line_1",
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
        status="classified",
    )
    db_session.add(act)
    await db_session.commit()
    return act


@pytest.mark.asyncio
async def test_compute_activity_success(
    db_session: AsyncSession,
    seed_test_factors: list[EmissionFactor],
    sample_activity: ActivityData,
) -> None:
    """Test successful emission computation, calculation record, status update, and audit log."""
    calc_service = CalculationService(db_session)
    calc = await calc_service.compute_activity(sample_activity.id)

    assert calc is not None
    assert isinstance(calc, Calculation)
    assert calc.result_tco2e == Decimal("0.38590000")
    assert "1000" in calc.formula_applied
    assert "0.3859" in calc.formula_applied

    # Verify ActivityData updated
    updated_act = await db_session.get(ActivityData, sample_activity.id)
    assert updated_act is not None
    assert updated_act.status == "computed"

    # Verify AuditLogEntry written
    audit_res = await db_session.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.entity_id == sample_activity.id,
            AuditLogEntry.action == "CALCULATE",
        )
    )
    audit_entry = audit_res.first()
    assert audit_entry is not None
    assert audit_entry.detail["result_tco2e"] == "0.38590000"
    assert "formula_applied" in audit_entry.detail


@pytest.mark.asyncio
async def test_compute_activity_missing_factor_marks_pending_factor(
    db_session: AsyncSession,
    seed_test_factors: list[EmissionFactor],
) -> None:
    """If no factor matches, activity is flagged pending_factor and
    audit logged (never hallucinated).
    """
    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        raw_line_ref="test_line_missing",
        activity_type="unknown_industrial_emission",
        quantity=Decimal("500"),
        unit="kg",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_TEST",
        scope=1,
        ghg_category="Other",
        classification_confidence=0.8,
        status="classified",
    )
    db_session.add(act)
    await db_session.commit()

    calc_service = CalculationService(db_session)
    calc = await calc_service.compute_activity(act.id)

    assert calc is None

    # Activity status must be pending_factor
    updated_act = await db_session.get(ActivityData, act.id)
    assert updated_act is not None
    assert updated_act.status == "pending_factor"

    # Audit log entry created for missing factor
    audit_res = await db_session.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.entity_id == act.id,
            AuditLogEntry.action == "CALCULATE_FAILED_MISSING_FACTOR",
        )
    )
    audit_entry = audit_res.first()
    assert audit_entry is not None
    assert "No matching factor found" in audit_entry.detail["reason"]


@pytest.mark.asyncio
async def test_batch_compute_for_document(
    db_session: AsyncSession,
    seed_test_factors: list[EmissionFactor],
) -> None:
    """Batch compute calculates all activities belonging to a source document."""
    doc_id = uuid.uuid4()
    act1 = ActivityData(
        id=uuid.uuid4(),
        source_document_id=doc_id,
        entity_id=uuid.uuid4(),
        raw_line_ref="doc_line_1",
        activity_type="electricity_purchase",
        quantity=Decimal("2000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_TEST",
        scope=2,
        ghg_category="Purchased Electricity",
        status="classified",
    )
    act2 = ActivityData(
        id=uuid.uuid4(),
        source_document_id=doc_id,
        entity_id=uuid.uuid4(),
        raw_line_ref="doc_line_2",
        activity_type="electricity_purchase",
        quantity=Decimal("1000"),
        unit="kWh",
        geography="US-CA",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_TEST",
        scope=2,
        ghg_category="Purchased Electricity",
        status="classified",
    )
    db_session.add_all([act1, act2])
    await db_session.commit()

    calc_service = CalculationService(db_session)
    results = await calc_service.compute_document_activities(doc_id)

    assert len(results["computed"]) == 2
    assert len(results["pending_factor"]) == 0
    assert len(results["errors"]) == 0
