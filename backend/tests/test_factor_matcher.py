"""Tests for emission factor matching pure function."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.emission_factor import EmissionFactor
from app.services.factor_matcher import MatchResult, match_emission_factor


@pytest.fixture
def sample_factor_library() -> list[EmissionFactor]:
    """Sample in-memory emission factor library with regional, national, and global entries."""
    return [
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
            source="DEFRA",
            source_version="2025",
            activity_type="electricity_purchase",
            geography="GB",
            unit="kWh",
            factor_value=Decimal("0.20493"),
            factor_unit="kgCO2e/kWh",
            published_date=date(2025, 6, 1),
            effective_from=date(2025, 1, 1),
            effective_to=None,
        ),
        EmissionFactor(
            id=uuid.uuid4(),
            source="DEFRA",
            source_version="2025",
            activity_type="business_travel_air",
            geography="GLO",
            unit="passenger.km",
            factor_value=Decimal("0.158"),
            factor_unit="kgCO2e/passenger.km",
            published_date=date(2025, 6, 1),
            effective_from=date(2025, 1, 1),
            effective_to=None,
        ),
        EmissionFactor(
            id=uuid.uuid4(),
            source="EPA_GHG_Hub",
            source_version="2024",
            activity_type="stationary_combustion_diesel",
            geography="US",
            unit="gallons",
            factor_value=Decimal("10.15"),
            factor_unit="kgCO2e/gallon",
            published_date=date(2024, 1, 1),
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 12, 31),
        ),
        EmissionFactor(
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
            effective_to=None,
        ),
    ]


def test_match_exact_regional_geography(sample_factor_library: list[EmissionFactor]) -> None:
    """Exact regional match (US-CA) preferred over national fallback (US)."""
    result = match_emission_factor(
        activity_type="electricity_purchase",
        geography="US-CA",
        activity_date=date(2025, 3, 1),
        available_factors=sample_factor_library,
    )
    assert isinstance(result, MatchResult)
    assert result.matched is True
    assert result.factor is not None
    assert result.factor.geography == "US-CA"
    assert result.factor.factor_value == Decimal("0.2154")
    assert result.fallback_level == "exact"


def test_match_fallback_to_national_geography(sample_factor_library: list[EmissionFactor]) -> None:
    """Regional geography (US-TX) falls back to national (US)."""
    result = match_emission_factor(
        activity_type="electricity_purchase",
        geography="US-TX",
        activity_date=date(2025, 3, 1),
        available_factors=sample_factor_library,
    )
    assert result.matched is True
    assert result.factor is not None
    assert result.factor.geography == "US"
    assert result.factor.factor_value == Decimal("0.3859")
    assert result.fallback_level == "national_fallback"


def test_match_fallback_to_global_geography(sample_factor_library: list[EmissionFactor]) -> None:
    """Activity in US falls back to GLO when only GLO factor exists."""
    result = match_emission_factor(
        activity_type="business_travel_air",
        geography="US",
        activity_date=date(2025, 3, 1),
        available_factors=sample_factor_library,
    )
    assert result.matched is True
    assert result.factor is not None
    assert result.factor.geography == "GLO"
    assert result.fallback_level == "global_fallback"


def test_match_effective_date_boundary(sample_factor_library: list[EmissionFactor]) -> None:
    """Matches correct factor version based on activity date."""
    # 2024 date matches 2024 factor
    result_2024 = match_emission_factor(
        activity_type="stationary_combustion_diesel",
        geography="US",
        activity_date=date(2024, 6, 15),
        available_factors=sample_factor_library,
    )
    assert result_2024.matched is True
    assert result_2024.factor is not None
    assert result_2024.factor.source_version == "2024"
    assert result_2024.factor.factor_value == Decimal("10.15")

    # 2025 date matches 2025 factor
    result_2025 = match_emission_factor(
        activity_type="stationary_combustion_diesel",
        geography="US",
        activity_date=date(2025, 2, 1),
        available_factors=sample_factor_library,
    )
    assert result_2025.matched is True
    assert result_2025.factor is not None
    assert result_2025.factor.source_version == "2025"
    assert result_2025.factor.factor_value == Decimal("10.21")


def test_match_missing_factor_returns_unmatched(
    sample_factor_library: list[EmissionFactor],
) -> None:
    """Missing factor returns matched=False and factor=None (never hallucinates)."""
    result = match_emission_factor(
        activity_type="industrial_process_cement",
        geography="US",
        activity_date=date(2025, 1, 1),
        available_factors=sample_factor_library,
    )
    assert result.matched is False
    assert result.factor is None
    assert result.fallback_level == "none"
    assert "No matching factor found" in result.reason
