"""Unit tests for Decarbonization Scenario Simulator."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.schemas.simulator import AppliedLever, SimulationRequest
from app.services.scenario_simulator import ScenarioSimulator


@pytest.mark.asyncio
async def test_scenario_simulator_supported_levers(db_session: AsyncSession) -> None:
    """Verify supported levers catalog has comprehensive definitions."""
    simulator = ScenarioSimulator(db_session)
    levers = simulator.get_lever_catalog()
    assert len(levers) >= 4
    lever_ids = [lev.lever_id for lev in levers]
    assert "SOLAR_PPA_GRID_ELEC" in lever_ids
    assert "EV_FLEET_TRANSITION" in lever_ids
    assert "HEAT_PUMP_RETROFIT" in lever_ids
    assert "BUSINESS_TRAVEL_MODAL_SHIFT" in lever_ids


@pytest.mark.asyncio
async def test_scenario_simulator_run_simulation(db_session: AsyncSession) -> None:
    """Verify deterministic simulation math, emissions abatement, and MACC ROI ranking."""
    entity_id = uuid.uuid4()
    source_doc_id = uuid.uuid4()

    # 1. Emission factor
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

    # 2. Electricity line: 100,000 kWh -> 40.0 tCO2e
    act_elec = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="elec_1",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("100000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_ELEC",
        scope=2,
        ghg_category="Scope 2.1 Purchased Electricity",
        status="calculated",
    )
    db_session.add(act_elec)
    await db_session.flush()

    calc_elec = Calculation(
        activity_data_id=act_elec.id,
        emission_factor_id=factor.id,
        formula_applied="100000 * 0.4",
        result_tco2e=Decimal("40.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_elec)

    # 3. Natural gas line: 10,000 therms -> 53.0 tCO2e
    act_gas = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="gas_1",
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
        status="calculated",
    )
    db_session.add(act_gas)
    await db_session.flush()

    calc_gas = Calculation(
        activity_data_id=act_gas.id,
        emission_factor_id=factor.id,
        formula_applied="10000 * 5.3",
        result_tco2e=Decimal("53.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_gas)

    # 4. Flight line: 50,000 km -> 10.0 tCO2e
    act_flight = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="flight_1",
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
        status="calculated",
    )
    db_session.add(act_flight)
    await db_session.flush()

    calc_flight = Calculation(
        activity_data_id=act_flight.id,
        emission_factor_id=factor.id,
        formula_applied="50000 * 0.2",
        result_tco2e=Decimal("10.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_flight)

    await db_session.commit()

    # Total baseline: 40.0 + 53.0 + 10.0 = 103.0 tCO2e
    simulator = ScenarioSimulator(db_session)

    # Apply 2 levers:
    # 1. Solar PPA on 50% grid elec -> 40.0 * 0.5 * 1.0 = 20.0 tCO2e abated
    # 2. Business travel modal shift on 60% flights -> 10.0 * 0.6 * 0.85 = 5.1 tCO2e abated
    request = SimulationRequest(
        entity_id=entity_id,
        reporting_period="2025",
        applied_levers=[
            AppliedLever(
                lever_id="SOLAR_PPA_GRID_ELEC",
                implementation_rate=0.5,
                custom_capex_usd=0.0,
                custom_annual_opex_delta_usd=-2000.0,  # $2,000 savings
            ),
            AppliedLever(
                lever_id="BUSINESS_TRAVEL_MODAL_SHIFT",
                implementation_rate=0.6,
                custom_capex_usd=0.0,
                custom_annual_opex_delta_usd=-5000.0,  # $5,000 savings
            ),
        ],
        target_reduction_percent=20.0,
    )

    res = await simulator.simulate(request)

    assert res.entity_id == entity_id
    assert res.baseline_gross_tco2e == pytest.approx(103.0, rel=1e-2)
    assert res.total_reduction_tco2e == pytest.approx(25.1, rel=1e-2)
    assert res.simulated_gross_tco2e == pytest.approx(77.9, rel=1e-2)
    assert res.total_reduction_percent == pytest.approx(24.37, rel=1e-1)
    assert res.target_met is True

    # Check ranked levers (MACC ranking)
    assert len(res.ranked_levers) == 2
    # Business travel: -$5,000 / 5.1 tCO2e = -$980.39/tCO2e
    # Solar PPA: -$2,000 / 20.0 tCO2e = -$100.00/tCO2e
    # Lower (more negative) MAC ranks first:
    assert res.ranked_levers[0].lever_id == "BUSINESS_TRAVEL_MODAL_SHIFT"
    assert res.ranked_levers[0].roi_rank == 1
    assert res.ranked_levers[1].lever_id == "SOLAR_PPA_GRID_ELEC"
    assert res.ranked_levers[1].roi_rank == 2
