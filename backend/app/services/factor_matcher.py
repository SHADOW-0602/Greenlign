"""Emission factor matching service.

Pure function matching on (activity_type, geography, effective_dates).
Implements regional-to-national fallback hierarchy (e.g. US-CA -> US -> GLO).
Activities with no matching factor return matched=False (never hallucinated).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.models.emission_factor import EmissionFactor


@dataclass(frozen=True)
class MatchResult:
    """Result of an emission factor matching operation."""

    matched: bool
    factor: EmissionFactor | None
    fallback_level: str  # "exact", "national_fallback", "global_fallback", "none"
    reason: str


def _get_geography_hierarchy(geography: str) -> list[tuple[str, str]]:
    """Return ordered search candidates for a geography code.

    Examples:
        'US-CA' -> [('US-CA', 'exact'), ('US', 'national_fallback'), ('GLO', 'global_fallback')]
        'US'    -> [('US', 'exact'), ('GLO', 'global_fallback')]
        'GB'    -> [('GB', 'exact'), ('GLO', 'global_fallback')]
        'GLO'   -> [('GLO', 'exact')]
    """
    clean_geo = geography.strip().upper()
    candidates: list[tuple[str, str]] = [(clean_geo, "exact")]

    if "-" in clean_geo:
        # e.g. "US-CA" -> national is "US"
        national = clean_geo.split("-")[0].strip()
        if national and national != clean_geo:
            candidates.append((national, "national_fallback"))

    if clean_geo != "GLO":
        candidates.append(("GLO", "global_fallback"))

    return candidates


def match_emission_factor(
    activity_type: str,
    geography: str,
    activity_date: date,
    available_factors: Sequence[EmissionFactor],
) -> MatchResult:
    """Find best matching emission factor using deterministic geographic fallback and dates.

    Args:
        activity_type: Canonical activity type string (e.g. 'electricity_purchase').
        geography: Geographic ISO region code (e.g. 'US-CA', 'US', 'GB').
        activity_date: Date the activity occurred (to match effective_from/to bounds).
        available_factors: Collection of available EmissionFactor database records.

    Returns:
        MatchResult with matched=True and the chosen factor, or matched=False if no factor fits.
    """
    clean_activity = activity_type.strip().lower()
    geo_candidates = _get_geography_hierarchy(geography)

    # Filter factors by activity_type and date validity
    active_candidates: list[EmissionFactor] = []
    for factor in available_factors:
        if factor.activity_type.strip().lower() != clean_activity:
            continue
        # Check effective date bounds
        if factor.effective_from <= activity_date:
            if factor.effective_to is None or factor.effective_to >= activity_date:
                active_candidates.append(factor)

    if not active_candidates:
        return MatchResult(
            matched=False,
            factor=None,
            fallback_level="none",
            reason=(
                f"No matching factor found for activity_type '{activity_type}' "
                f"active on {activity_date}"
            ),
        )

    # Search in order of geographic specificity
    for candidate_geo, level in geo_candidates:
        matching_for_geo = [
            f for f in active_candidates if f.geography.strip().upper() == candidate_geo
        ]
        if matching_for_geo:
            # Sort by published_date descending to prefer latest published factor
            chosen_factor = sorted(
                matching_for_geo,
                key=lambda f: (f.published_date, f.effective_from),
                reverse=True,
            )[0]
            return MatchResult(
                matched=True,
                factor=chosen_factor,
                fallback_level=level,
                reason=(
                    f"Matched factor '{chosen_factor.source}' "
                    f"({chosen_factor.source_version}) via {level}"
                ),
            )

    return MatchResult(
        matched=False,
        factor=None,
        fallback_level="none",
        reason=(
            f"No factor found matching geography '{geography}' or any fallback "
            f"hierarchy for activity '{activity_type}'"
        ),
    )
