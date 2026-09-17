"""Entity Eligibility Checker for regulatory ESG frameworks.

Evaluates applicability criteria:
- California SB 253: Total annual revenue > $1B USD and doing business in California.
- CSRD ESRS E1: Large EU undertaking (> 250 employees and €50M turnover or €25M balance sheet)
  or Non-EU parent (> €150M EU turnover).
- GHG Protocol Corporate Standard: Universally applicable.
"""

from decimal import Decimal
from typing import Final

from app.schemas.disclosure import (
    EntityEligibilityRequest,
    EntityEligibilityResponse,
    FrameworkEligibilityStatus,
    SupportedFramework,
)

CA_SB253_REVENUE_THRESHOLD_USD: Final[Decimal] = Decimal("1000000000")
CSRD_TURNOVER_LARGE_EUR: Final[Decimal] = Decimal("50000000")
CSRD_BALANCE_SHEET_LARGE_EUR: Final[Decimal] = Decimal("25000000")
CSRD_EMPLOYEE_LARGE_THRESHOLD: Final[int] = 250
CSRD_NON_EU_TURNOVER_EUR: Final[Decimal] = Decimal("150000000")


class IneligibleFrameworkError(ValueError):
    """Raised when attempting to generate a disclosure report for an ineligible framework."""


class EligibilityChecker:
    """Evaluates regulatory framework applicability for a given corporate profile."""

    @classmethod
    def check_ca_sb253(cls, profile: EntityEligibilityRequest) -> FrameworkEligibilityStatus:
        """Check eligibility under California Senate Bill 253."""
        revenue_ok = profile.annual_revenue_usd > CA_SB253_REVENUE_THRESHOLD_USD
        california_ok = profile.does_business_in_california

        if revenue_ok and california_ok:
            return FrameworkEligibilityStatus(
                framework="CA_SB253",
                is_eligible=True,
                reason=(
                    f"Entity is eligible: exceeds $1B USD annual revenue threshold "
                    f"(${profile.annual_revenue_usd:,.2f}) and conducts business in California."
                ),
                mandatory_scopes=[1, 2, 3],
                reporting_deadline_notes=(
                    "Scope 1 & 2 mandatory starting 2026; Scope 3 mandatory starting 2027."
                ),
            )

        reasons: list[str] = []
        if not revenue_ok:
            reasons.append(
                f"Annual revenue (${profile.annual_revenue_usd:,.2f}) does not "
                f"exceed $1,000,000,000 threshold"
            )
        if not california_ok:
            reasons.append("Entity does not conduct business in California")

        return FrameworkEligibilityStatus(
            framework="CA_SB253",
            is_eligible=False,
            reason="; ".join(reasons) + ".",
            mandatory_scopes=[1, 2, 3],
            reporting_deadline_notes="N/A (Ineligible)",
        )

    @classmethod
    def check_csrd(cls, profile: EntityEligibilityRequest) -> FrameworkEligibilityStatus:
        """Check eligibility under EU Corporate Sustainability Reporting Directive (ESRS E1)."""
        if profile.is_eu_parent:
            # Large undertaking: satisfies at least 2 of 3 criteria
            crit_employees = profile.employee_count > CSRD_EMPLOYEE_LARGE_THRESHOLD
            crit_turnover = profile.eu_net_turnover_eur > CSRD_TURNOVER_LARGE_EUR
            crit_balance = profile.balance_sheet_total_eur > CSRD_BALANCE_SHEET_LARGE_EUR
            matched_count = sum([crit_employees, crit_turnover, crit_balance])

            if matched_count >= 2:
                details = (
                    f"(Employees: {profile.employee_count}, "
                    f"Turnover: €{profile.eu_net_turnover_eur:,.2f}, "
                    f"Balance Sheet: €{profile.balance_sheet_total_eur:,.2f})."
                )
                return FrameworkEligibilityStatus(
                    framework="CSRD_ESRS_E1",
                    is_eligible=True,
                    reason=f"EU large undertaking meeting {matched_count}/3 criteria {details}",
                    mandatory_scopes=[1, 2, 3],
                    reporting_deadline_notes=(
                        "ESRS E1 disclosure required annually with statutory audit assurance."
                    ),
                )
            return FrameworkEligibilityStatus(
                framework="CSRD_ESRS_E1",
                is_eligible=False,
                reason=(
                    f"EU entity only satisfied {matched_count}/3 criteria for large undertakings "
                    f"(minimum 2 required)."
                ),
                mandatory_scopes=[1, 2, 3],
                reporting_deadline_notes="N/A (Ineligible)",
            )

        # Non-EU parent rule: EU turnover > €150M
        if profile.eu_net_turnover_eur > CSRD_NON_EU_TURNOVER_EUR:
            return FrameworkEligibilityStatus(
                framework="CSRD_ESRS_E1",
                is_eligible=True,
                reason=(
                    f"Non-EU parent entity with EU net turnover "
                    f"(€{profile.eu_net_turnover_eur:,.2f}) exceeding €150,000,000 threshold."
                ),
                mandatory_scopes=[1, 2, 3],
                reporting_deadline_notes=(
                    "Non-EU group reporting mandatory from financial year 2028."
                ),
            )

        return FrameworkEligibilityStatus(
            framework="CSRD_ESRS_E1",
            is_eligible=False,
            reason=(
                f"Non-EU entity's EU turnover (€{profile.eu_net_turnover_eur:,.2f}) "
                f"does not exceed the €150,000,000 threshold."
            ),
            mandatory_scopes=[1, 2, 3],
            reporting_deadline_notes="N/A (Ineligible)",
        )

    @classmethod
    def check_ghg_protocol(cls, profile: EntityEligibilityRequest) -> FrameworkEligibilityStatus:
        """Check eligibility under standard GHG Protocol Corporate Standard."""
        return FrameworkEligibilityStatus(
            framework="GHG_PROTOCOL",
            is_eligible=True,
            reason=(
                "Universal standard available for voluntary and general "
                "corporate GHG inventory reporting."
            ),
            mandatory_scopes=[1, 2, 3],
            reporting_deadline_notes="Self-determined corporate sustainability reporting cycle.",
        )

    @classmethod
    def check_all(cls, profile: EntityEligibilityRequest) -> EntityEligibilityResponse:
        """Evaluate profile across all supported reporting frameworks."""
        return EntityEligibilityResponse(
            frameworks={
                "CA_SB253": cls.check_ca_sb253(profile),
                "CSRD_ESRS_E1": cls.check_csrd(profile),
                "GHG_PROTOCOL": cls.check_ghg_protocol(profile),
            }
        )

    @classmethod
    def validate_eligibility_for_framework(
        cls,
        framework: SupportedFramework,
        profile: EntityEligibilityRequest | None,
    ) -> None:
        """Raise IneligibleFrameworkError if profile is provided and does not qualify."""
        if profile is None:
            return

        status = cls.check_all(profile).frameworks[framework]
        if not status.is_eligible:
            raise IneligibleFrameworkError(
                f"Entity is not eligible to generate {framework} disclosure: {status.reason}"
            )
