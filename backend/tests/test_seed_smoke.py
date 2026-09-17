"""Integration smoke test: seed script loads factors into database."""
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emission_factor import EmissionFactor
from app.seeds.factors import FACTOR_FILES, seed_factors


@pytest.mark.asyncio
async def test_seed_factors_inserts_rows(db_session: AsyncSession) -> None:
    """seed_factors(session=db_session) must insert at least 4 rows (2 EPA + 2 DEFRA)."""
    assert len(FACTOR_FILES) >= 2
    inserted = await seed_factors(session=db_session)
    assert inserted >= 4, f"Expected at least 4 factors inserted, got {inserted}"

    result = await db_session.scalars(select(EmissionFactor))
    factors = result.all()
    assert len(factors) == inserted
    assert len(factors) >= 4, f"Expected at least 4 factors in db, got {len(factors)}"

    # Verify EPA GHG Hub electricity purchase factor
    epa_elec = next(
        f
        for f in factors
        if f.source == "EPA_GHG_Hub" and f.activity_type == "electricity_purchase"
    )
    assert epa_elec.factor_value == Decimal("0.3859")
    assert epa_elec.factor_unit == "kgCO2e/kWh"
    assert epa_elec.unit == "kWh"
    assert epa_elec.geography == "US"
    assert epa_elec.source_version == "2025"

    # Verify DEFRA electricity purchase factor
    defra_elec = next(
        f
        for f in factors
        if f.source == "DEFRA" and f.activity_type == "electricity_purchase"
    )
    assert defra_elec.factor_value == Decimal("0.20493")
    assert defra_elec.factor_unit == "kgCO2e/kWh"
    assert defra_elec.geography == "GB"


@pytest.mark.asyncio
async def test_seed_factors_is_idempotent(db_session: AsyncSession) -> None:
    """Re-running seed_factors must not insert duplicate rows."""
    first_run_count = await seed_factors(session=db_session)
    assert first_run_count >= 4

    second_run_count = await seed_factors(session=db_session)
    assert second_run_count == 0

    result = await db_session.scalars(select(EmissionFactor))
    total_factors = result.all()
    assert len(total_factors) == first_run_count


@pytest.mark.asyncio
async def test_seed_factors_default_session() -> None:
    """Calling seed_factors() without explicit session uses AsyncSessionLocal context manager."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.return_value = None
    mock_session.commit = AsyncMock()

    with patch("app.seeds.factors.AsyncSessionLocal") as mock_sessionmaker:
        mock_sessionmaker.return_value.__aenter__.return_value = mock_session
        mock_sessionmaker.return_value.__aexit__.return_value = None

        count = await seed_factors()
        assert count >= 4
        mock_sessionmaker.assert_called_once()
        mock_session.commit.assert_awaited()
