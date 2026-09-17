"""Deterministic GHG Emission Calculation Engine.

Pure Python arithmetic strictly using Decimal. Zero LLM calls in the call stack.
Performs dimension-safe unit conversion, factor multiplication, and
metric tonne (tCO2e) normalization.
"""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

# 8 decimal places for storing emission figures
DECIMAL_8_PLACES: Final[Decimal] = Decimal("0.00000001")


class IncompatibleUnitError(ValueError):
    """Raised when activity units cannot be converted to the emission factor denominator unit."""


@dataclass(frozen=True)
class CalculationResult:
    """Immutable result of a deterministic emission calculation."""

    result_tco2e: Decimal
    formula_applied: str
    activity_quantity: Decimal
    activity_unit: str
    factor_value: Decimal
    factor_unit: str
    unit_conversion_ratio: Decimal
    emissions_conversion_ratio: Decimal


# Base unit conversion ratios: to_unit = from_unit * ratio
# Grouped by physical dimension to enforce dimensional safety
UNIT_CONVERSIONS: Final[dict[tuple[str, str], Decimal]] = {
    # Energy: Base unit is kWh
    ("kwh", "kwh"): Decimal("1"),
    ("mwh", "kwh"): Decimal("1000"),
    ("kwh", "mwh"): Decimal("0.001"),
    ("therms", "therms"): Decimal("1"),
    ("therm", "therm"): Decimal("1"),
    ("therm", "therms"): Decimal("1"),
    ("therms", "therm"): Decimal("1"),
    ("mmbtu", "therms"): Decimal("10"),
    ("mmbtu", "therm"): Decimal("10"),
    ("therms", "mmbtu"): Decimal("0.1"),
    ("therm", "mmbtu"): Decimal("0.1"),
    ("ccf", "therms"): Decimal("1.037"),
    ("ccf", "therm"): Decimal("1.037"),
    ("gj", "kwh"): Decimal("277.77777778"),
    ("mj", "kwh"): Decimal("0.27777778"),

    # Volume: Base unit is liters
    ("liters", "liters"): Decimal("1"),
    ("liter", "liter"): Decimal("1"),
    ("liter", "liters"): Decimal("1"),
    ("liters", "liter"): Decimal("1"),
    ("l", "liters"): Decimal("1"),
    ("l", "liter"): Decimal("1"),
    ("gallons", "liters"): Decimal("3.785411784"),
    ("gallon", "liters"): Decimal("3.785411784"),
    ("gallons", "liter"): Decimal("3.785411784"),
    ("gallon", "liter"): Decimal("3.785411784"),
    ("gallons", "gallon"): Decimal("1"),
    ("gallon", "gallons"): Decimal("1"),
    ("gallon", "gallon"): Decimal("1"),
    ("gallons", "gallons"): Decimal("1"),
    ("gal", "liters"): Decimal("3.785411784"),
    ("gal", "liter"): Decimal("3.785411784"),
    ("gal", "gallon"): Decimal("1"),
    ("gal", "gallons"): Decimal("1"),

    # Mass: Base unit is kg
    ("kg", "kg"): Decimal("1"),
    ("g", "kg"): Decimal("0.001"),
    ("tonne", "kg"): Decimal("1000"),
    ("tonnes", "kg"): Decimal("1000"),
    ("metric_ton", "kg"): Decimal("1000"),
    ("ton", "kg"): Decimal("907.18474"),
    ("tons", "kg"): Decimal("907.18474"),
    ("lb", "kg"): Decimal("0.45359237"),
    ("lbs", "kg"): Decimal("0.45359237"),
    ("pounds", "kg"): Decimal("0.45359237"),
    ("pound", "kg"): Decimal("0.45359237"),

    # Distance / Passenger Transport: Base unit is km
    ("km", "km"): Decimal("1"),
    ("miles", "km"): Decimal("1.609344"),
    ("mile", "km"): Decimal("1.609344"),
    ("passenger.km", "passenger.km"): Decimal("1"),
    ("passenger.miles", "passenger.km"): Decimal("1.609344"),
    ("passenger.mile", "passenger.km"): Decimal("1.609344"),
    ("p.km", "passenger.km"): Decimal("1"),
    ("p.mile", "passenger.km"): Decimal("1.609344"),

    # Freight Transport: Base unit is tonne.km
    ("tonne.km", "tonne.km"): Decimal("1"),
    ("ton.miles", "tonne.km"): Decimal("1.459972"),
    ("ton.mile", "tonne.km"): Decimal("1.459972"),

    # Direct items / count
    ("units", "units"): Decimal("1"),
    ("unit", "units"): Decimal("1"),
    ("items", "items"): Decimal("1"),
    ("room_nights", "room_nights"): Decimal("1"),
    ("nights", "room_nights"): Decimal("1"),
    ("usd", "usd"): Decimal("1"),
}

# Emission numerator to metric tonnes of CO2e (tCO2e)
EMISSION_NUMERATOR_CONVERSIONS: Final[dict[str, Decimal]] = {
    "tco2e": Decimal("1"),
    "mtco2e": Decimal("1"),
    "tonne_co2e": Decimal("1"),
    "kgco2e": Decimal("0.001"),
    "kg_co2e": Decimal("0.001"),
    "gco2e": Decimal("0.000001"),
    "g_co2e": Decimal("0.000001"),
    "lbco2e": Decimal("0.00045359237"),
    "lb_co2e": Decimal("0.00045359237"),
}


def normalize_unit_string(unit: str) -> str:
    """Normalize unit string for dictionary lookup (strip spaces, lowercase)."""
    return unit.strip().lower().replace(" ", "")


def parse_factor_unit(factor_unit: str) -> tuple[str, str]:
    """Parse compound factor unit like 'kgCO2e/kWh' into ('kgCO2e', 'kWh')."""
    parts = factor_unit.split("/")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return factor_unit.strip(), "unit"


def get_emission_numerator_ratio(numerator_str: str) -> Decimal:
    """Return multiplier to convert emission numerator into metric tonnes (tCO2e)."""
    clean_num = normalize_unit_string(numerator_str)
    # Remove standard punctuation or casing variations
    clean_num = re.sub(r"[_\s\-]", "", clean_num)
    if clean_num in EMISSION_NUMERATOR_CONVERSIONS:
        return EMISSION_NUMERATOR_CONVERSIONS[clean_num]
    if "kg" in clean_num:
        return Decimal("0.001")
    if "g" in clean_num and "kg" not in clean_num:
        return Decimal("0.000001")
    if "lb" in clean_num:
        return Decimal("0.00045359237")
    return Decimal("1")


def convert_quantity(
    quantity: Decimal,
    from_unit: str,
    to_unit: str,
) -> tuple[Decimal, Decimal]:
    """Convert an activity quantity from one unit to another within the same physical dimension."""
    norm_from = normalize_unit_string(from_unit)
    norm_to = normalize_unit_string(to_unit)

    if norm_from == norm_to:
        return quantity, Decimal("1")

    # Direct conversion
    key = (norm_from, norm_to)
    if key in UNIT_CONVERSIONS:
        ratio = UNIT_CONVERSIONS[key]
        return quantity * ratio, ratio

    # Inverse lookup: if (to, from) is known, invert ratio
    inverse_key = (norm_to, norm_from)
    if inverse_key in UNIT_CONVERSIONS:
        ratio = Decimal("1") / UNIT_CONVERSIONS[inverse_key]
        return quantity * ratio, ratio

    raise IncompatibleUnitError(
        f"Cannot convert quantity from '{from_unit}' to factor unit '{to_unit}'. "
        "Units belong to incompatible physical dimensions."
    )


def compute_emission(
    quantity: Decimal,
    activity_unit: str,
    factor_value: Decimal,
    factor_unit: str,
) -> CalculationResult:
    """Execute deterministic multiplication and unit conversion to calculate tCO2e."""
    if not isinstance(quantity, Decimal):
        quantity = Decimal(str(quantity))
    if not isinstance(factor_value, Decimal):
        factor_value = Decimal(str(factor_value))

    num_str, denom_str = parse_factor_unit(factor_unit)

    # Convert activity quantity to factor denominator unit
    converted_qty, unit_ratio = convert_quantity(
        quantity=quantity,
        from_unit=activity_unit,
        to_unit=denom_str,
    )

    # Multiplier to convert emission numerator (e.g. kgCO2e) to metric tonnes (tCO2e)
    emission_ratio = get_emission_numerator_ratio(num_str)

    # Unrounded raw calculation
    raw_tco2e = converted_qty * factor_value * emission_ratio

    # Quantize to 8 decimal places using standard round half up
    result_tco2e = raw_tco2e.quantize(DECIMAL_8_PLACES, rounding=ROUND_HALF_UP)

    # Generate human-readable formula
    steps = [f"{quantity} {activity_unit}"]
    if unit_ratio != Decimal("1"):
        steps.append(f"[converted: {converted_qty} {denom_str}]")
    steps.append(f"* {factor_value} {factor_unit}")
    if emission_ratio == Decimal("0.001"):
        steps.append("/ 1000 [kg to t]")
    elif emission_ratio == Decimal("0.000001"):
        steps.append("/ 1000000 [g to t]")
    elif emission_ratio != Decimal("1"):
        steps.append(f"* {emission_ratio} [to tCO2e]")

    formula_applied = f"{' '.join(steps)} = {result_tco2e} tCO2e"

    return CalculationResult(
        result_tco2e=result_tco2e,
        formula_applied=formula_applied,
        activity_quantity=quantity,
        activity_unit=activity_unit,
        factor_value=factor_value,
        factor_unit=factor_unit,
        unit_conversion_ratio=unit_ratio,
        emissions_conversion_ratio=emission_ratio,
    )
