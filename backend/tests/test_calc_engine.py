"""Tests for the deterministic emission calculation engine."""

from decimal import Decimal

import pytest

from app.services.calc_engine import (
    CalculationResult,
    IncompatibleUnitError,
    compute_emission,
    convert_quantity,
)


def test_compute_emission_direct_epa_electricity() -> None:
    """Benchmark: 1,000 kWh US electricity @ 0.3859 kgCO2e/kWh = 0.3859 tCO2e."""
    result = compute_emission(
        quantity=Decimal("1000"),
        activity_unit="kWh",
        factor_value=Decimal("0.3859"),
        factor_unit="kgCO2e/kWh",
    )
    assert isinstance(result, CalculationResult)
    assert result.result_tco2e == Decimal("0.38590000")
    assert "1000" in result.formula_applied
    assert "0.3859" in result.formula_applied
    assert "tCO2e" in result.formula_applied


def test_compute_emission_mwh_to_kwh_conversion() -> None:
    """Benchmark: 2.5 MWh converted to kWh (2,500 kWh) @ 0.3859 kgCO2e/kWh."""
    result = compute_emission(
        quantity=Decimal("2.5"),
        activity_unit="MWh",
        factor_value=Decimal("0.3859"),
        factor_unit="kgCO2e/kWh",
    )
    assert result.result_tco2e == Decimal("0.96475000")
    assert result.unit_conversion_ratio == Decimal("1000")


def test_compute_emission_natural_gas_therms() -> None:
    """Benchmark: 100 therms natural gas @ 5.3 kgCO2e/therm = 0.53 tCO2e."""
    result = compute_emission(
        quantity=Decimal("100"),
        activity_unit="therms",
        factor_value=Decimal("5.3"),
        factor_unit="kgCO2e/therm",
    )
    assert result.result_tco2e == Decimal("0.53000000")


def test_compute_emission_natural_gas_mmbtu_conversion() -> None:
    """Benchmark: 15 MMBtu natural gas (150 therms) @ 5.3 kgCO2e/therm."""
    result = compute_emission(
        quantity=Decimal("15"),
        activity_unit="MMBtu",
        factor_value=Decimal("5.3"),
        factor_unit="kgCO2e/therm",
    )
    assert result.result_tco2e == Decimal("0.79500000")
    assert result.unit_conversion_ratio == Decimal("10")


def test_compute_emission_defra_diesel_liters() -> None:
    """Benchmark: 50 liters diesel @ 2.705 kgCO2e/liter = 0.13525 tCO2e."""
    result = compute_emission(
        quantity=Decimal("50"),
        activity_unit="liters",
        factor_value=Decimal("2.705"),
        factor_unit="kgCO2e/liter",
    )
    assert result.result_tco2e == Decimal("0.13525000")


def test_compute_emission_defra_diesel_gallons_conversion() -> None:
    """Benchmark: 20 US gallons diesel converted to liters @ 2.705 kgCO2e/liter."""
    result = compute_emission(
        quantity=Decimal("20"),
        activity_unit="gallons",
        factor_value=Decimal("2.705"),
        factor_unit="kgCO2e/liter",
    )
    # 20 * 3.785411784 * 2.705 / 1000 = 0.20479078
    assert result.result_tco2e == Decimal("0.20479078")


def test_compute_emission_flight_passenger_km() -> None:
    """Benchmark: 500 passenger.km @ 0.158 kgCO2e/passenger.km = 0.079 tCO2e."""
    result = compute_emission(
        quantity=Decimal("500"),
        activity_unit="passenger.km",
        factor_value=Decimal("0.158"),
        factor_unit="kgCO2e/passenger.km",
    )
    assert result.result_tco2e == Decimal("0.07900000")


def test_compute_emission_flight_passenger_miles_conversion() -> None:
    """Benchmark: 300 passenger.miles converted to passenger.km @ 0.158 kgCO2e/p.km."""
    result = compute_emission(
        quantity=Decimal("300"),
        activity_unit="passenger.miles",
        factor_value=Decimal("0.158"),
        factor_unit="kgCO2e/passenger.km",
    )
    # 300 * 1.609344 * 0.158 / 1000 = 0.0762829056 -> rounds half up to 0.07628291
    assert result.result_tco2e == Decimal("0.07628291")


def test_compute_emission_refrigerant_r410a() -> None:
    """Benchmark: 2 kg R-410A leakage @ 2088 kgCO2e/kg = 4.176 tCO2e."""
    result = compute_emission(
        quantity=Decimal("2"),
        activity_unit="kg",
        factor_value=Decimal("2088"),
        factor_unit="kgCO2e/kg",
    )
    assert result.result_tco2e == Decimal("4.17600000")


def test_compute_emission_direct_tco2e_factor() -> None:
    """Benchmark: Factor already in tCO2e per unit."""
    result = compute_emission(
        quantity=Decimal("10"),
        activity_unit="tonne",
        factor_value=Decimal("1.85"),
        factor_unit="tCO2e/tonne",
    )
    assert result.result_tco2e == Decimal("18.50000000")
    assert result.emissions_conversion_ratio == Decimal("1")


def test_compute_emission_gco2e_factor() -> None:
    """Benchmark: Factor in gCO2e per unit."""
    # 1000 kWh * 385.9 gCO2e/kWh / 1,000,000 = 0.3859 tCO2e
    result = compute_emission(
        quantity=Decimal("1000"),
        activity_unit="kWh",
        factor_value=Decimal("385.9"),
        factor_unit="gCO2e/kWh",
    )
    assert result.result_tco2e == Decimal("0.38590000")
    assert result.emissions_conversion_ratio == Decimal("0.000001")


def test_compute_emission_incompatible_units_raises() -> None:
    """Attempting to compute emissions with incompatible dimensions raises IncompatibleUnitError."""
    with pytest.raises(IncompatibleUnitError, match="Cannot convert"):
        compute_emission(
            quantity=Decimal("100"),
            activity_unit="kWh",
            factor_value=Decimal("2.705"),
            factor_unit="kgCO2e/liter",
        )


def test_convert_quantity_same_unit() -> None:
    qty, ratio = convert_quantity(Decimal("50"), "kWh", "kWh")
    assert qty == Decimal("50")
    assert ratio == Decimal("1")
