"""Tests for regulatory Disclosure Generator (aggregation, citation, and PDF creation)."""

import io
import uuid
from datetime import date
from decimal import Decimal

import pytest
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.schemas.disclosure import EntityEligibilityRequest
from app.services.disclosure_generator import DisclosureGenerator
from app.services.eligibility_checker import IneligibleFrameworkError


@pytest.fixture
async def setup_disclosure_inventory(
    db_session: AsyncSession,
) -> tuple[uuid.UUID, list[Calculation]]:
    """Create test activity and calculations across Scope 1, 2, and 3."""
    entity_id = uuid.uuid4()

    # Factor
    factor = EmissionFactor(
        id=uuid.uuid4(),
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="stationary_combustion_diesel",
        geography="US",
        unit="gallons",
        factor_value=Decimal("10.21"),
        factor_unit="kgCO2e/gallon",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add(factor)

    # Scope 1 Activity & Calc
    act_s1 = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        raw_line_ref="fuel_log_1",
        activity_type="stationary_combustion_diesel",
        quantity=Decimal("100"),
        unit="gallons",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_FUEL",
        scope=1,
        ghg_category="Stationary Combustion",
        status="computed",
    )
    db_session.add(act_s1)
    calc_s1 = Calculation(
        id=uuid.uuid4(),
        activity_data_id=act_s1.id,
        emission_factor_id=factor.id,
        formula_applied="100 gal * 10.21 kgCO2e/gal / 1000 = 1.02100000 tCO2e",
        result_tco2e=Decimal("1.02100000"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_s1)

    # Scope 2 Activity & Calc
    act_s2 = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        raw_line_ref="elec_bill_1",
        activity_type="electricity_purchase",
        quantity=Decimal("2000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_ELEC",
        scope=2,
        ghg_category="Purchased Electricity",
        status="computed",
    )
    db_session.add(act_s2)
    calc_s2 = Calculation(
        id=uuid.uuid4(),
        activity_data_id=act_s2.id,
        emission_factor_id=factor.id,
        formula_applied="2000 kWh * 0.3859 kgCO2e/kWh / 1000 = 0.77180000 tCO2e",
        result_tco2e=Decimal("0.77180000"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_s2)

    # Scope 3 Activity & Calc
    act_s3 = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        raw_line_ref="travel_log_1",
        activity_type="business_travel_air",
        quantity=Decimal("500"),
        unit="passenger.km",
        geography="GLO",
        period_start=date(2025, 2, 1),
        period_end=date(2025, 2, 28),
        supplier_ref="TOKEN_SUPP_AIR",
        scope=3,
        ghg_category="Business Travel",
        status="computed",
    )
    db_session.add(act_s3)
    calc_s3 = Calculation(
        id=uuid.uuid4(),
        activity_data_id=act_s3.id,
        emission_factor_id=factor.id,
        formula_applied="500 p.km * 0.158 kgCO2e/p.km / 1000 = 0.07900000 tCO2e",
        result_tco2e=Decimal("0.07900000"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_s3)

    await db_session.commit()
    return entity_id, [calc_s1, calc_s2, calc_s3]


@pytest.mark.asyncio
async def test_generate_ca_sb253_disclosure_success(
    db_session: AsyncSession,
    setup_disclosure_inventory: tuple[uuid.UUID, list[Calculation]],
) -> None:
    """Generate CA SB 253 disclosure with aggregated scopes and PDF citations."""
    entity_id, calcs = setup_disclosure_inventory

    generator = DisclosureGenerator(db_session)
    profile = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("1500000000"),
        does_business_in_california=True,
    )

    detail, pdf_bytes = await generator.generate_disclosure(
        entity_id=entity_id,
        framework="CA_SB253",
        reporting_period="2025",
        entity_profile=profile,
    )

    # Verify deterministic arithmetic totals
    # S1: 1.02100000, S2: 0.77180000, S3: 0.07900000 -> Total: 1.87180000
    assert detail.scope_1_tco2e == Decimal("1.02100000")
    assert detail.scope_2_tco2e == Decimal("0.77180000")
    assert detail.scope_3_tco2e == Decimal("0.07900000")
    assert detail.total_tco2e == Decimal("1.87180000")

    # Verify line_item_refs
    assert len(detail.line_item_refs) == 3
    for c in calcs:
        assert c.id in detail.line_item_refs

    # Verify PDF content and citations
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 500
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    extracted_text = "".join(p.extract_text() or "" for p in reader.pages)
    assert "California Senate Bill 253" in extracted_text
    assert "1.8718" in extracted_text
    assert "Stationary Combustion" in extracted_text


@pytest.mark.asyncio
async def test_generate_disclosure_ineligible_raises_error(
    db_session: AsyncSession,
    setup_disclosure_inventory: tuple[uuid.UUID, list[Calculation]],
) -> None:
    """Attempting to generate CA SB 253 for ineligible entity raises IneligibleFrameworkError."""
    entity_id, _ = setup_disclosure_inventory

    generator = DisclosureGenerator(db_session)
    ineligible_profile = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("500000000"),
        does_business_in_california=False,
    )

    with pytest.raises(IneligibleFrameworkError, match="not eligible"):
        await generator.generate_disclosure(
            entity_id=entity_id,
            framework="CA_SB253",
            reporting_period="2025",
            entity_profile=ineligible_profile,
        )
