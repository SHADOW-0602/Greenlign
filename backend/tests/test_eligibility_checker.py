"""Tests for Entity Eligibility Checker across CA SB 253, CSRD, and GHG Protocol."""

from decimal import Decimal

from app.schemas.disclosure import EntityEligibilityRequest
from app.services.eligibility_checker import EligibilityChecker


def test_ca_sb253_eligible_over_1_billion_and_california_nexus() -> None:
    """Revenue > $1B USD and doing business in California meets CA SB 253 criteria."""
    req = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("1200000000"),
        does_business_in_california=True,
    )
    res = EligibilityChecker.check_all(req)

    ca_status = res.frameworks["CA_SB253"]
    assert ca_status.is_eligible is True
    assert "eligible" in ca_status.reason.lower()
    assert 1 in ca_status.mandatory_scopes
    assert 2 in ca_status.mandatory_scopes
    assert 3 in ca_status.mandatory_scopes


def test_ca_sb253_ineligible_revenue_below_threshold() -> None:
    """Revenue <= $1B USD is ineligible for CA SB 253."""
    req = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("850000000"),
        does_business_in_california=True,
    )
    res = EligibilityChecker.check_all(req)

    ca_status = res.frameworks["CA_SB253"]
    assert ca_status.is_eligible is False
    assert "does not exceed $1,000,000,000" in ca_status.reason


def test_ca_sb253_ineligible_no_california_nexus() -> None:
    """Revenue > $1B USD but no California operations is ineligible for CA SB 253."""
    req = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("2000000000"),
        does_business_in_california=False,
    )
    res = EligibilityChecker.check_all(req)

    ca_status = res.frameworks["CA_SB253"]
    assert ca_status.is_eligible is False
    assert "does not conduct business in california" in ca_status.reason.lower()


def test_csrd_esrs_e1_eu_large_undertaking() -> None:
    """EU entity meeting 2 of 3 criteria (>250 staff, >€50M turnover) is eligible for CSRD."""
    req = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("100000000"),
        does_business_in_california=False,
        eu_net_turnover_eur=Decimal("60000000"),
        balance_sheet_total_eur=Decimal("30000000"),
        employee_count=350,
        is_eu_parent=True,
    )
    res = EligibilityChecker.check_all(req)

    csrd_status = res.frameworks["CSRD_ESRS_E1"]
    assert csrd_status.is_eligible is True
    assert "large undertaking" in csrd_status.reason.lower()


def test_csrd_esrs_e1_non_eu_parent_high_turnover() -> None:
    """Non-EU parent with EU net turnover > €150M is eligible under CSRD non-EU threshold."""
    req = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("3000000000"),
        does_business_in_california=False,
        eu_net_turnover_eur=Decimal("200000000"),
        is_eu_parent=False,
    )
    res = EligibilityChecker.check_all(req)

    csrd_status = res.frameworks["CSRD_ESRS_E1"]
    assert csrd_status.is_eligible is True
    assert "non-eu parent" in csrd_status.reason.lower()


def test_ghg_protocol_always_eligible() -> None:
    """GHG Protocol Corporate Standard is universally applicable to any entity."""
    req = EntityEligibilityRequest(
        annual_revenue_usd=Decimal("50000"),
        does_business_in_california=False,
    )
    res = EligibilityChecker.check_all(req)

    ghg_status = res.frameworks["GHG_PROTOCOL"]
    assert ghg_status.is_eligible is True
    assert "universal standard" in ghg_status.reason.lower()
