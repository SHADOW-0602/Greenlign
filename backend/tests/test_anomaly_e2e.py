"""End-to-end integration test for Phase 6: Anomaly Detection and Greenwashing Verification."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor


@pytest.mark.asyncio
async def test_anomaly_detection_and_greenwashing_e2e(db_session: AsyncSession) -> None:
    """Full lifecycle: scan -> narrative check -> auditor resolution -> audit trail."""
    entity_id = uuid.uuid4()

    # 1. Setup Emission Factors
    gas_factor = EmissionFactor(
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
    elec_factor = EmissionFactor(
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="electricity_purchase",
        geography="US",
        unit="kWh",
        factor_value=Decimal("0.0003859"),
        factor_unit="tCO2e/kWh",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add_all([gas_factor, elec_factor])
    await db_session.flush()

    # 2. Baseline Period (2024): 20,000 therms gas (106 tCO2e), 50,000 kWh elec (19.295 tCO2e)
    act_gas_2024 = ActivityData(
        raw_line_ref="gas_2024",
        entity_id=entity_id,
        activity_type="natural_gas_combustion",
        quantity=Decimal("20000"),
        unit="therms",
        geography="US",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        supplier_ref="TOKEN_SUPP_GAS",
        scope=1,
        ghg_category="Scope 1 Stationary Combustion",
        status="calculated",
    )
    act_elec_2024 = ActivityData(
        raw_line_ref="elec_2024",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("50000"),
        unit="kWh",
        geography="US",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        supplier_ref="TOKEN_SUPP_ELEC",
        scope=2,
        ghg_category="Scope 2 Electricity",
        status="calculated",
    )
    db_session.add_all([act_gas_2024, act_elec_2024])
    await db_session.flush()

    calc_gas_2024 = Calculation(
        activity_data_id=act_gas_2024.id,
        emission_factor_id=gas_factor.id,
        formula_applied="20000 * 0.0053",
        result_tco2e=Decimal("106.0"),
        computed_by="calc_engine_v1",
    )
    calc_elec_2024 = Calculation(
        activity_data_id=act_elec_2024.id,
        emission_factor_id=elec_factor.id,
        formula_applied="50000 * 0.0003859",
        result_tco2e=Decimal("19.295"),
        computed_by="calc_engine_v1",
    )
    db_session.add_all([calc_gas_2024, calc_elec_2024])

    # 3. Current Period (2025):
    # - Gas: 19,000 therms, emissions reported as 10.6 tCO2e (injected 90% drop)
    # - Elec: normal rows + extreme outlier row
    act_gas_2025 = ActivityData(
        raw_line_ref="gas_2025",
        entity_id=entity_id,
        activity_type="natural_gas_combustion",
        quantity=Decimal("19000"),
        unit="therms",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="TOKEN_SUPP_GAS",
        scope=1,
        ghg_category="Scope 1 Stationary Combustion",
        status="calculated",
    )
    db_session.add(act_gas_2025)
    await db_session.flush()

    calc_gas_2025 = Calculation(
        activity_data_id=act_gas_2025.id,
        emission_factor_id=gas_factor.id,
        formula_applied="injected synthetic drop",
        result_tco2e=Decimal("10.6"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_gas_2025)

    # Add electricity items (10 normal items so cohort size allows Z >= 3.0)
    for idx in range(10):
        qty = 10000 + idx * 100
        a = ActivityData(
            raw_line_ref=f"elec_2025_{idx}",
            entity_id=entity_id,
            activity_type="electricity_purchase",
            quantity=Decimal(str(qty)),
            unit="kWh",
            geography="US",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 6, 30),
            supplier_ref="TOKEN_SUPP_ELEC",
            scope=2,
            ghg_category="Scope 2 Electricity",
            status="calculated",
        )
        db_session.add(a)
        await db_session.flush()
        c = Calculation(
            activity_data_id=a.id,
            emission_factor_id=elec_factor.id,
            formula_applied="qty * factor",
            result_tco2e=Decimal(str(qty)) * Decimal("0.0003859"),
            computed_by="calc_engine_v1",
        )
        db_session.add(c)

    # Injected intensity outlier electricity line item
    outlier_a = ActivityData(
        raw_line_ref="elec_2025_outlier",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("5000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 7, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="TOKEN_SUPP_ELEC",
        scope=2,
        ghg_category="Scope 2 Electricity",
        status="calculated",
    )
    db_session.add(outlier_a)
    await db_session.flush()
    outlier_c = Calculation(
        activity_data_id=outlier_a.id,
        emission_factor_id=elec_factor.id,
        formula_applied="corrupted calculation",
        result_tco2e=Decimal("250.0"),  # Extreme intensity outlier
        computed_by="calc_engine_v1",
    )
    db_session.add(outlier_c)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 4. Run Statistical & Scope Anomaly Scan
            scan_res = await client.post(
                "/api/anomalies/scan",
                json={
                    "entity_id": str(entity_id),
                    "current_period": "2025",
                    "baseline_period": "2024",
                    "yoy_threshold_pct": 50.0,
                    "zscore_threshold": 3.0,
                },
            )
            assert scan_res.status_code == 200
            scan_data = scan_res.json()
            assert scan_data["flags_detected_count"] >= 2
            flag_types = {f["flag_type"] for f in scan_data["flags"]}
            assert "YOY_DROP" in flag_types
            assert "INTENSITY_OUTLIER" in flag_types

            drop_flag = next(f for f in scan_data["flags"] if f["flag_type"] == "YOY_DROP")
            assert drop_flag["status"] == "OPEN"

            # 5. Check Corporate Sustainability Statement (Greenwashing Detection)
            narrative = (
                "In 2025, through our aggressive sustainability program, "
                "we achieved an 80% reduction in total gross corporate emissions."
            )
            narr_res = await client.post(
                "/api/anomalies/check-narrative",
                json={
                    "entity_id": str(entity_id),
                    "reporting_period": "2025",
                    "baseline_period": "2024",
                    "narrative_text": narrative,
                },
            )
            assert narr_res.status_code == 200
            narr_data = narr_res.json()
            assert narr_data["overall_status"] == "FLAGGED"
            assert len(narr_data["findings"]) >= 1

            # 6. Auditor Review & Resolution
            resolve_res = await client.patch(
                f"/api/anomalies/{drop_flag['id']}/resolve",
                json={
                    "status": "CONFIRMED",
                    "notes": "Verified that natural gas usage at plant B was missing meter logs.",
                    "actor": "senior_auditor_alice",
                },
            )
            assert resolve_res.status_code == 200
            resolved_flag = resolve_res.json()
            assert resolved_flag["status"] == "CONFIRMED"
            assert resolved_flag["resolved_by"] == "senior_auditor_alice"

            # 7. Verify Audit Log Trail
            logs_res = await db_session.scalars(
                select(AuditLogEntry)
                .where(AuditLogEntry.action.in_(["ANOMALY_SCAN", "RESOLVE_ANOMALY"]))
            )
            logs = list(logs_res.all())
            assert len(logs) >= 2
            scan_log = next(log for log in logs if log.action == "ANOMALY_SCAN")
            assert scan_log.entity_id == entity_id

            resolve_log = next(log for log in logs if log.action == "RESOLVE_ANOMALY")
            assert resolve_log.actor == "senior_auditor_alice"
            assert resolve_log.detail["status"] == "CONFIRMED"
    finally:
        app.dependency_overrides.pop(get_db, None)
