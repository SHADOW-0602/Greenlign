"""Unit tests for DashboardService."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.anomaly_flag import AnomalyFlag
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.services.dashboard_service import DashboardService


@pytest.mark.asyncio
async def test_dashboard_summary_aggregation(db_session: AsyncSession) -> None:
    """Test aggregating emissions across Scope 1, 2, and 3, hotspots, and trends."""
    entity_id = uuid.uuid4()
    source_doc_id = uuid.uuid4()

    # Create an emission factor
    factor = EmissionFactor(
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
    await db_session.flush()

    # Scope 1: Stationary Combustion (Gas)
    act_s1 = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="row_1",
        entity_id=entity_id,
        activity_type="natural_gas",
        quantity=Decimal("10000"),
        unit="therms",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_GAS",
        scope=1,
        ghg_category="Scope 1.1 Stationary Combustion",
        classification_confidence=0.99,
        status="calculated",
    )
    db_session.add(act_s1)
    await db_session.flush()

    calc_s1 = Calculation(
        activity_data_id=act_s1.id,
        emission_factor_id=factor.id,
        formula_applied="10000 therms * 5.3 kgCO2e/therm",
        result_tco2e=Decimal("53.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_s1)

    # Scope 2: Purchased Electricity
    act_s2 = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="row_2",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("100000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_GRID",
        scope=2,
        ghg_category="Scope 2.1 Purchased Electricity",
        classification_confidence=0.98,
        status="calculated",
    )
    db_session.add(act_s2)
    await db_session.flush()

    calc_s2 = Calculation(
        activity_data_id=act_s2.id,
        emission_factor_id=factor.id,
        formula_applied="100000 kWh * 0.3859 kgCO2e/kWh",
        result_tco2e=Decimal("38.59"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_s2)

    # Scope 3: Business Travel Flights
    act_s3 = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="row_3",
        entity_id=entity_id,
        activity_type="flight",
        quantity=Decimal("50000"),
        unit="km",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_AIR",
        scope=3,
        ghg_category="Scope 3.6 Business Travel",
        classification_confidence=0.95,
        status="calculated",
    )
    db_session.add(act_s3)
    await db_session.flush()

    calc_s3 = Calculation(
        activity_data_id=act_s3.id,
        emission_factor_id=factor.id,
        formula_applied="50000 km * 0.16 kgCO2e/km",
        result_tco2e=Decimal("8.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_s3)

    # Add an AnomalyFlag
    flag = AnomalyFlag(
        entity_id=entity_id,
        reporting_period="2025",
        flag_type="YOY_SPIKE",
        severity="CRITICAL",
        title="Surge in gas emissions",
        description="Gas surged > 100%",
        status="OPEN",
        details_json={},
    )
    db_session.add(flag)

    await db_session.commit()

    # Execute service
    service = DashboardService(db_session)
    summary = await service.get_dashboard_summary(entity_id=entity_id, reporting_period="2025")

    assert summary.entity_id == entity_id
    assert summary.reporting_period == "2025"
    assert summary.total_calculations == 3
    assert summary.gross_emissions_tco2e == pytest.approx(99.59, rel=1e-2)

    # Scope breakdown assertions
    scopes = {s.scope: s for s in summary.scope_breakdown}
    assert 1 in scopes and 2 in scopes and 3 in scopes
    assert scopes[1].total_tco2e == pytest.approx(53.0)
    assert scopes[2].total_tco2e == pytest.approx(38.59)
    assert scopes[3].total_tco2e == pytest.approx(8.0)

    # Hotspots assertions
    assert len(summary.top_hotspots) >= 3
    assert summary.top_hotspots[0].ghg_category == "Scope 1.1 Stationary Combustion"
    assert summary.top_hotspots[0].total_tco2e == pytest.approx(53.0)

    # Anomalies count assertions
    assert summary.open_anomalies_count == 1
    assert summary.critical_anomalies_count == 1
