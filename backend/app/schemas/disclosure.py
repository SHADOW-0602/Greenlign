"""Pydantic schemas for regulatory disclosures and eligibility checks."""

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SupportedFramework = Literal["CA_SB253", "CSRD_ESRS_E1", "GHG_PROTOCOL"]


class EntityEligibilityRequest(BaseModel):
    """Entity profile parameters used to evaluate regulatory disclosure eligibility."""

    annual_revenue_usd: Decimal = Field(
        ..., description="Total annual revenue in USD for the prior fiscal year."
    )
    does_business_in_california: bool = Field(
        False, description="Whether the entity operates or conducts business in California."
    )
    eu_net_turnover_eur: Decimal = Field(
        Decimal("0"), description="Net turnover generated within the European Union (EUR)."
    )
    balance_sheet_total_eur: Decimal = Field(
        Decimal("0"), description="Total balance sheet assets in EUR."
    )
    employee_count: int = Field(
        0, ge=0, description="Average number of employees over the fiscal year."
    )
    is_eu_parent: bool = Field(
        False, description="Whether the parent entity is incorporated in an EU member state."
    )


class FrameworkEligibilityStatus(BaseModel):
    """Eligibility status and reasoning for a specific framework."""

    framework: SupportedFramework
    is_eligible: bool
    reason: str
    mandatory_scopes: list[int]
    reporting_deadline_notes: str


class EntityEligibilityResponse(BaseModel):
    """Comprehensive eligibility results across all reporting frameworks."""

    frameworks: dict[SupportedFramework, FrameworkEligibilityStatus]


class GenerateDisclosureRequest(BaseModel):
    """Payload to trigger disclosure report generation."""

    entity_id: uuid.UUID
    framework: SupportedFramework
    reporting_period: str = Field(..., description="e.g. '2025' or '2025-Q1'")
    entity_profile: EntityEligibilityRequest | None = None


class CategoryEmissionsSummary(BaseModel):
    """Aggregated emissions and calculation citations for a specific GHG category."""

    scope: int
    ghg_category: str
    total_tco2e: Decimal
    line_item_count: int
    calculation_ids: list[uuid.UUID]


class ScopeEmissionsSummary(BaseModel):
    """Aggregated emissions for an entire Scope."""

    scope: int
    total_tco2e: Decimal
    categories: list[CategoryEmissionsSummary]


class DisclosureDetailResponse(BaseModel):
    """Detailed disclosure summary with scope totals and category breakdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_id: uuid.UUID
    framework: str
    reporting_period: str
    status: str
    generated_document_ref: str | None = None
    total_tco2e: Decimal
    scope_1_tco2e: Decimal
    scope_2_tco2e: Decimal
    scope_3_tco2e: Decimal
    scope_breakdown: list[ScopeEmissionsSummary]
    line_item_refs: list[uuid.UUID]
    metadata_json: dict[str, Any] = Field(default_factory=dict)
