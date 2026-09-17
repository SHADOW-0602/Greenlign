"""End-to-End Integration Test for GHG Accounting Pipeline.

Verifies complete flow:
1. Seed factors from official factor tables (EPA & DEFRA).
2. Parse raw ingestion data (ERP CSV format).
3. Classify GHG Protocol scope & category.
4. Deterministically match emission factors with geographic fallback.
5. Compute exact tCO2e emissions using pure Decimal arithmetic.
6. Verify against hand-calculated benchmark (1,000 kWh US electricity = 0.3859 tCO2e).
7. Verify immutable audit log trail for calculations.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.seeds.factors import seed_factors
from app.services.calculation_service import CalculationService
from app.services.classification_service import ClassificationService
from app.services.tabular_parser import TabularParser


@pytest.mark.asyncio
async def test_end_to_end_calculation_pipeline(db_session: AsyncSession) -> None:
    """Run full pipeline and assert exact benchmark equality."""
    # Step 1: Seed factor library
    seed_count = await seed_factors(session=db_session)
    assert seed_count > 0

    # Step 2: Parse raw CSV invoice data
    csv_data = (
        b"activity_type,quantity,unit,geography,period_start,period_end,supplier,line_id\n"
        b"electricity_purchase,1000,kWh,US,2025-01-01,2025-01-31,Consolidated Edison,line_101\n"
        b"natural_gas_combustion,50,therms,US,2025-01-01,2025-01-31,National Grid,line_102\n"
        b"electricity_purchase,2500,kWh,US-CA,2025-02-01,2025-02-28,PG&E,line_103\n"
    )

    parser = TabularParser()
    rows = parser.parse_csv(csv_data)
    assert len(rows) == 3

    entity_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    # Insert into ActivityData
    activities: list[ActivityData] = []
    for r in rows:
        act = ActivityData(
            id=uuid.uuid4(),
            entity_id=entity_id,
            source_document_id=doc_id,
            raw_line_ref=r.raw_line_ref,
            activity_type=r.activity_type,
            quantity=r.quantity,
            unit=r.unit,
            geography=r.geography,
            period_start=r.period_start,
            period_end=r.period_end,
            supplier_ref=r.supplier_ref,
            status="pending_review",
        )
        activities.append(act)
        db_session.add(act)
    await db_session.commit()

    # Step 3: Classify scope & category
    classifier = ClassificationService()
    classified_acts = await classifier.batch_classify(
        session=db_session, document_id=doc_id
    )
    assert len(classified_acts) == 3
    for act in classified_acts:
        assert act.status == "classified"
        assert act.scope is not None

    # Step 4 & 5: Compute emissions deterministically
    calc_service = CalculationService(db_session)
    summary = await calc_service.compute_document_activities(
        source_document_id=doc_id, actor="e2e_pipeline_runner"
    )

    assert len(summary["computed"]) == 3
    assert len(summary["pending_factor"]) == 0
    assert len(summary["errors"]) == 0

    # Step 6: Verify hand-calculated benchmark
    # Line 101: 1,000 kWh @ 0.3859 kgCO2e/kWh / 1000 = 0.3859 tCO2e
    calcs_res = await db_session.scalars(
        select(Calculation)
        .join(ActivityData, Calculation.activity_data_id == ActivityData.id)
        .where(ActivityData.source_document_id == doc_id)
    )
    calcs = list(calcs_res.all())
    assert len(calcs) == 3

    calc_by_ref: dict[str, Calculation] = {}
    for c in calcs:
        activity_item = await db_session.get(ActivityData, c.activity_data_id)
        assert activity_item is not None
        calc_by_ref[activity_item.raw_line_ref] = c

    # Assert Line 101 benchmark
    c_elec_us = calc_by_ref["line_101"]
    assert c_elec_us.result_tco2e == Decimal("0.38590000")
    assert "0.3859" in c_elec_us.formula_applied

    # Assert Line 102 benchmark: 50 therms @ 5.306 kgCO2e/therm / 1000 = 0.2653 tCO2e
    c_gas = calc_by_ref["line_102"]
    assert c_gas.result_tco2e == Decimal("0.26530000")

    # Assert Line 103 benchmark: 2,500 kWh CA electricity @ 0.2154 kgCO2e/kWh / 1000 = 0.5385 tCO2e
    c_elec_ca = calc_by_ref["line_103"]
    assert c_elec_ca.result_tco2e == Decimal("0.53850000")

    # Step 7: Verify Audit Log entries
    audit_res = await db_session.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.action == "CALCULATE",
            AuditLogEntry.actor == "e2e_pipeline_runner",
        )
    )
    audit_entries = audit_res.all()
    assert len(audit_entries) == 3
