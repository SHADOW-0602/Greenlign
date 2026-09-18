from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeverDefinition(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lever_id: str = Field(..., description="Unique identifier of the decarbonization lever")
    title: str = Field(..., description="Human-readable title of the intervention")
    description: str = Field(..., description="Operational details and mechanism of abatement")
    target_scope: int = Field(..., description="Primary GHG Scope impacted (1, 2, or 3)")
    target_activity_type: str = Field(
        ..., description="Matching ActivityData.activity_type substring or code"
    )
    default_capex_usd: float = Field(default=0.0, description="Typical CapEx baseline in USD")
    default_annual_opex_delta_usd: float = Field(
        default=0.0, description="Annual operating expenditure delta (negative for net savings)"
    )


class AppliedLever(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lever_id: str = Field(..., description="Identifier matching a supported lever")
    implementation_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Scale of deployment from 0.0 (0%) to 1.0 (100%)",
    )
    custom_capex_usd: float | None = Field(
        default=None, description="Optional override for capital expenditure"
    )
    custom_annual_opex_delta_usd: float | None = Field(
        default=None, description="Optional override for annual OpEx impact (negative = savings)"
    )


class SimulationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: UUID = Field(..., description="Target corporate entity UUID")
    reporting_period: str = Field(..., description="Baseline period to simulate against, e.g. 2025")
    applied_levers: list[AppliedLever] = Field(
        default_factory=list, description="List of decarbonization levers to apply"
    )
    target_reduction_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional corporate science-based target percentage (e.g. 50% by 2030)",
    )


class LeverImpactResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lever_id: str
    title: str
    scope: int
    baseline_emissions_tco2e: float
    simulated_emissions_tco2e: float
    reduction_tco2e: float
    reduction_percent: float
    annualized_net_cost_usd: float
    marginal_abatement_cost_usd_per_tco2e: float
    roi_rank: int


class SimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: UUID
    reporting_period: str
    baseline_gross_tco2e: float
    simulated_gross_tco2e: float
    total_reduction_tco2e: float
    total_reduction_percent: float
    net_annual_cost_usd: float
    target_met: bool | None = None
    ranked_levers: list[LeverImpactResult] = Field(default_factory=list)
