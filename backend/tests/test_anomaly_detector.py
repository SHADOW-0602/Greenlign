"""Unit tests for AnomalyDetector: statistical variance and narrative consistency."""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.services.anomaly_detector import AnomalyDetector


@pytest.mark.asyncio
async def test_yoy_variance_drop_without_activity_change(db_session: AsyncSession) -> None:
    """An unexplained 90% drop in emissions without activity drop triggers YOY_DROP flag."""
    entity_id = uuid.uuid4()

    # 1. Setup factor
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

    # 2. Baseline year 2024: 10,000 therms -> 53 tCO2e
    act_2024 = ActivityData(
        raw_line_ref="row:1",
        entity_id=entity_id,
        activity_type="natural_gas_combustion",
        quantity=Decimal("10000"),
        unit="therms",
        geography="US",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        supplier_ref="TOKEN_SUPP_GAS",
        scope=1,
        ghg_category="Scope 1 Stationary Combustion",
        status="calculated",
    )
    db_session.add(act_2024)
    await db_session.flush()

    calc_2024 = Calculation(
        activity_data_id=act_2024.id,
        emission_factor_id=factor.id,
        formula_applied="quantity * factor",
        result_tco2e=Decimal("53.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_2024)

    # 3. Current year 2025: 9,500 therms (5% drop), emissions reported as 5.3 tCO2e (90% drop)
    act_2025 = ActivityData(
        raw_line_ref="row:2",
        entity_id=entity_id,
        activity_type="natural_gas_combustion",
        quantity=Decimal("9500"),
        unit="therms",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="TOKEN_SUPP_GAS",
        scope=1,
        ghg_category="Scope 1 Stationary Combustion",
        status="calculated",
    )
    db_session.add(act_2025)
    await db_session.flush()

    calc_2025 = Calculation(
        activity_data_id=act_2025.id,
        emission_factor_id=factor.id,
        formula_applied="quantity * factor",
        result_tco2e=Decimal("5.3"),  # Injected synthetic anomaly
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_2025)
    await db_session.commit()

    detector = AnomalyDetector(db_session)
    flags = await detector.check_yoy_variance(
        entity_id=entity_id,
        current_period="2025",
        baseline_period="2024",
        threshold_pct=Decimal("50.0"),
    )

    assert len(flags) >= 1
    drop_flag = next((f for f in flags if f.flag_type == "YOY_DROP"), None)
    assert drop_flag is not None
    assert drop_flag.severity == "CRITICAL"
    assert "drop" in drop_flag.title.lower()
    assert drop_flag.details_json["pct_change"] <= -80.0


@pytest.mark.asyncio
async def test_yoy_variance_proportional_change_no_flag(db_session: AsyncSession) -> None:
    """Proportional changes in both activity and emissions do not trigger an anomaly flag."""
    entity_id = uuid.uuid4()

    factor = EmissionFactor(
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
    db_session.add(factor)
    await db_session.flush()

    # 2024
    act_2024 = ActivityData(
        raw_line_ref="row:1",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("10000"),
        unit="kWh",
        geography="US",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        supplier_ref="TOKEN_SUPP_ELEC",
        scope=2,
        ghg_category="Scope 2 Electricity",
        status="calculated",
    )
    db_session.add(act_2024)
    await db_session.flush()
    calc_2024 = Calculation(
        activity_data_id=act_2024.id,
        emission_factor_id=factor.id,
        formula_applied="quantity * factor",
        result_tco2e=Decimal("3.859"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_2024)

    # 2025 (10% activity reduction, 10% emission reduction)
    act_2025 = ActivityData(
        raw_line_ref="row:2",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("9000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="TOKEN_SUPP_ELEC",
        scope=2,
        ghg_category="Scope 2 Electricity",
        status="calculated",
    )
    db_session.add(act_2025)
    await db_session.flush()
    calc_2025 = Calculation(
        activity_data_id=act_2025.id,
        emission_factor_id=factor.id,
        formula_applied="quantity * factor",
        result_tco2e=Decimal("3.4731"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_2025)
    await db_session.commit()

    detector = AnomalyDetector(db_session)
    flags = await detector.check_yoy_variance(
        entity_id=entity_id,
        current_period="2025",
        baseline_period="2024",
    )

    assert len(flags) == 0


@pytest.mark.asyncio
async def test_intensity_outlier_detection(db_session: AsyncSession) -> None:
    """A data point with intensity > 3 standard deviations must trigger INTENSITY_OUTLIER."""
    entity_id = uuid.uuid4()

    factor = EmissionFactor(
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="freight_road",
        geography="US",
        unit="tonne.km",
        factor_value=Decimal("0.00016"),
        factor_unit="tCO2e/tonne.km",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add(factor)
    await db_session.flush()

    # Create 10 normal line items with intensity around 0.00016
    for i in range(10):
        act = ActivityData(
            raw_line_ref=f"row:{i}",
            entity_id=entity_id,
            activity_type="freight_road",
            quantity=Decimal("1000"),
            unit="tonne.km",
            geography="US",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            supplier_ref="TOKEN_SUPP_FLEET",
            scope=3,
            ghg_category="Scope 3 Upstream Transportation",
            status="calculated",
        )
        db_session.add(act)
        await db_session.flush()
        calc = Calculation(
            activity_data_id=act.id,
            emission_factor_id=factor.id,
            formula_applied="quantity * factor",
            result_tco2e=Decimal("0.16"),
            computed_by="calc_engine_v1",
        )
        db_session.add(calc)

    # Injected outlier line item: 100x intensity
    outlier_act = ActivityData(
        raw_line_ref="row:outlier",
        entity_id=entity_id,
        activity_type="freight_road",
        quantity=Decimal("1000"),
        unit="tonne.km",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_FLEET",
        scope=3,
        ghg_category="Scope 3 Upstream Transportation",
        status="calculated",
    )
    db_session.add(outlier_act)
    await db_session.flush()
    outlier_calc = Calculation(
        activity_data_id=outlier_act.id,
        emission_factor_id=factor.id,
        formula_applied="quantity * factor",
        result_tco2e=Decimal("16.0"),  # Extreme outlier
        computed_by="calc_engine_v1",
    )
    db_session.add(outlier_calc)
    await db_session.commit()

    detector = AnomalyDetector(db_session)
    flags = await detector.check_intensity_outliers(
        entity_id=entity_id,
        period="2025",
        zscore_cutoff=3.0,
    )

    assert len(flags) >= 1
    outlier_flag = next((f for f in flags if f.flag_type == "INTENSITY_OUTLIER"), None)
    assert outlier_flag is not None
    assert outlier_flag.details_json["z_score"] >= 3.0


@pytest.mark.asyncio
async def test_scope_completeness_missing_scope1(db_session: AsyncSession) -> None:
    """Omission of Scope 1 that was present in baseline triggers SCOPE_INCOMPLETENESS."""
    entity_id = uuid.uuid4()

    # 2024 had Scope 1 and Scope 2
    for sc, a_type in [(1, "natural_gas_combustion"), (2, "electricity_purchase")]:
        act = ActivityData(
            raw_line_ref="row:1",
            entity_id=entity_id,
            activity_type=a_type,
            quantity=Decimal("5000"),
            unit="kWh" if sc == 2 else "therms",
            geography="US",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            supplier_ref="TOKEN_SUPP_UTIL",
            scope=sc,
            status="calculated",
        )
        db_session.add(act)
        await db_session.flush()
        calc = Calculation(
            activity_data_id=act.id,
            emission_factor_id=uuid.uuid4(),
            formula_applied="x",
            result_tco2e=Decimal("10.0"),
            computed_by="calc_engine_v1",
        )
        db_session.add(calc)

    # 2025 has only Scope 2, Scope 1 is completely omitted
    act_2025 = ActivityData(
        raw_line_ref="row:2",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("5000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="TOKEN_SUPP_UTIL",
        scope=2,
        status="calculated",
    )
    db_session.add(act_2025)
    await db_session.flush()
    calc_2025 = Calculation(
        activity_data_id=act_2025.id,
        emission_factor_id=uuid.uuid4(),
        formula_applied="x",
        result_tco2e=Decimal("10.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_2025)
    await db_session.commit()

    detector = AnomalyDetector(db_session)
    flags = await detector.check_scope_completeness(
        entity_id=entity_id,
        current_period="2025",
        baseline_period="2024",
    )

    assert len(flags) >= 1
    omission = next((f for f in flags if f.flag_type == "SCOPE_INCOMPLETENESS"), None)
    assert omission is not None
    assert "Scope 1" in omission.description


@pytest.mark.asyncio
async def test_narrative_claim_evaluation_greenwashing(db_session: AsyncSession) -> None:
    """Text claiming 50% emissions reduction against actual 10% increase flags greenwashing."""
    entity_id = uuid.uuid4()

    explanation = (
        "Claimed 50% decrease directly contradicts verified records showing an increase "
        "from 200 tCO2e to 220 tCO2e."
    )
    mock_json = {
        "findings": [
            {
                "claim_text": "We reduced total operational emissions by 50% in 2025.",
                "verdict": "CONTRADICTED",
                "claimed_metric": "50% reduction",
                "actual_metric": "10.0% increase (+20.0 tCO2e)",
                "discrepancy_explanation": explanation,
            }
        ],
        "overall_status": "FLAGGED",
        "summary_text": "Found 1 contradicted claim indicating potential greenwashing.",
    }
    import json
    mock_chat_completion = MagicMock()
    mock_chat_completion.choices = [
        MagicMock(message=MagicMock(content=json.dumps(mock_json)))
    ]
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value = mock_chat_completion

    detector = AnomalyDetector(db_session)
    narrative = (
        "In our 2025 annual review, we reduced total operational emissions by 50% in 2025."
    )
    res = await detector.evaluate_narrative_claims(
        entity_id=entity_id,
        reporting_period="2025",
        narrative_text=narrative,
        baseline_period="2024",
        groq_client=mock_groq,
    )

    assert res.overall_status == "FLAGGED"
    assert len(res.findings) == 1
    assert res.findings[0].verdict == "CONTRADICTED"
    assert res.flag_id is not None
