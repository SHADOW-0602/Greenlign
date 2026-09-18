from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScopeMetric(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope: int = Field(..., description="GHG Scope (1, 2, or 3)")
    total_tco2e: float = Field(..., description="Emissions in metric tonnes CO2e")
    share_percentage: float = Field(..., description="Percentage of gross emissions (0-100)")


class CategoryHotspot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ghg_category: str = Field(..., description="GHG Protocol category name")
    scope: int = Field(..., description="GHG Scope (1, 2, or 3)")
    total_tco2e: float = Field(..., description="Total emissions in tCO2e")
    share_percentage: float = Field(..., description="Share of total gross emissions")
    activity_count: int = Field(..., description="Number of contributing activity line items")


class PeriodicTrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reporting_period: str = Field(..., description="Reporting period label, e.g. 2024 or 2025")
    scope1_tco2e: float = Field(default=0.0)
    scope2_tco2e: float = Field(default=0.0)
    scope3_tco2e: float = Field(default=0.0)
    total_tco2e: float = Field(default=0.0)


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: UUID
    reporting_period: str
    gross_emissions_tco2e: float = Field(..., description="Total corporate gross emissions")
    scope_breakdown: list[ScopeMetric] = Field(default_factory=list)
    top_hotspots: list[CategoryHotspot] = Field(default_factory=list)
    historical_trends: list[PeriodicTrendPoint] = Field(default_factory=list)
    total_calculations: int = Field(default=0)
    open_anomalies_count: int = Field(default=0)
    critical_anomalies_count: int = Field(default=0)
