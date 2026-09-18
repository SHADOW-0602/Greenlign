"""Decarbonization Scenario Simulator Engine.

Provides deterministic 'what-if' modeling for corporate carbon abatement levers,
reusing verified calculations, unit conversions, and computing Marginal Abatement
Cost Curves (MACC) to rank decarbonization ROI ($/tCO2e abated).
"""

from decimal import Decimal
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.calculation import Calculation
from app.schemas.simulator import (
    LeverDefinition,
    LeverImpactResult,
    SimulationRequest,
    SimulationResponse,
)

# Standard catalog of enterprise decarbonization interventions
SUPPORTED_LEVERS: Final[list[LeverDefinition]] = [
    LeverDefinition(
        lever_id="SOLAR_PPA_GRID_ELEC",
        title="On-Site Solar & Renewable Electricity PPA",
        description=(
            "Replace utility grid electricity consumption with certified "
            "zero-emissions renewable energy."
        ),
        target_scope=2,
        target_activity_type="electricity",
        default_capex_usd=0.0,
        default_annual_opex_delta_usd=-2500.0,
    ),
    LeverDefinition(
        lever_id="EV_FLEET_TRANSITION",
        title="Fleet Electrification (EV Transition)",
        description=(
            "Replace internal combustion diesel/gasoline fleet vehicles with "
            "high-efficiency electric vehicles."
        ),
        target_scope=1,
        target_activity_type="diesel",
        default_capex_usd=40000.0,
        default_annual_opex_delta_usd=-4000.0,
    ),
    LeverDefinition(
        lever_id="HEAT_PUMP_RETROFIT",
        title="Industrial Heat Pump & Thermal Efficiency Retrofit",
        description=(
            "Electrify space and process heating, transitioning from natural gas "
            "boilers to COP 3.5 heat pumps."
        ),
        target_scope=1,
        target_activity_type="natural_gas",
        default_capex_usd=35000.0,
        default_annual_opex_delta_usd=-1500.0,
    ),
    LeverDefinition(
        lever_id="SUPPLY_CHAIN_ENGAGEMENT",
        title="Scope 3 Supplier Decarbonization Standard",
        description=(
            "Procure low-carbon raw materials and mandate supplier emission "
            "reduction targets."
        ),
        target_scope=3,
        target_activity_type="purchased_goods",
        default_capex_usd=10000.0,
        default_annual_opex_delta_usd=1000.0,
    ),
    LeverDefinition(
        lever_id="BUSINESS_TRAVEL_MODAL_SHIFT",
        title="Corporate Travel Modal Shift (Rail & Virtual)",
        description=(
            "Shift short-haul business flights to high-speed rail and virtual "
            "collaboration platforms."
        ),
        target_scope=3,
        target_activity_type="flight",
        default_capex_usd=0.0,
        default_annual_opex_delta_usd=-10000.0,
    ),
]

# Abatement efficiencies for each intervention mechanism
LEVER_ABATEMENT_FACTORS: Final[dict[str, Decimal]] = {
    "SOLAR_PPA_GRID_ELEC": Decimal("1.00"),  # 100% emission reduction on replaced power
    "EV_FLEET_TRANSITION": Decimal("0.70"),  # 70% net reduction factoring in grid charging
    "HEAT_PUMP_RETROFIT": Decimal("0.65"),  # 65% net reduction with high-efficiency heat pumps
    "SUPPLY_CHAIN_ENGAGEMENT": Decimal("0.25"),  # 25% average supplier footprint reduction
    "BUSINESS_TRAVEL_MODAL_SHIFT": Decimal("0.85"),  # 85% reduction for rail/virtual shift
}


class ScenarioSimulator:
    """Deterministic decarbonization scenario simulator."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._lever_map: dict[str, LeverDefinition] = {
            item.lever_id: item for item in SUPPORTED_LEVERS
        }

    def get_lever_catalog(self) -> list[LeverDefinition]:
        """Return the catalog of supported decarbonization interventions."""
        return list(SUPPORTED_LEVERS)

    async def simulate(self, request: SimulationRequest) -> SimulationResponse:
        """Run deterministic what-if abatement simulation and rank levers by MAC ROI."""
        # 1. Fetch baseline calculations and activity data for this entity
        query = (
            select(Calculation, ActivityData)
            .join(ActivityData, Calculation.activity_data_id == ActivityData.id)
            .where(ActivityData.entity_id == request.entity_id)
        )
        res = await self.session.execute(query)
        all_rows = list(res.all())

        # Filter rows for the requested reporting period
        current_rows: list[tuple[Calculation, ActivityData]] = []
        for calc, act in all_rows:
            act_year = str(act.period_start.year)
            valid_periods = (
                act_year,
                f"{act_year}-Q1",
                f"{act_year}-Q2",
                f"{act_year}-Q3",
                f"{act_year}-Q4",
            )
            if request.reporting_period in valid_periods or request.reporting_period == act_year:
                current_rows.append((calc, act))

        if not current_rows and all_rows:
            current_rows = [(r[0], r[1]) for r in all_rows]

        baseline_gross = sum((calc.result_tco2e for calc, _ in current_rows), Decimal("0"))

        # 2. Evaluate each applied lever deterministically
        raw_impacts: list[dict[str, Any]] = []
        total_abated = Decimal("0")
        total_annual_cost = Decimal("0")

        for applied in request.applied_levers:
            lever_def = self._lever_map.get(applied.lever_id)
            if not lever_def:
                continue

            target_kw = lever_def.target_activity_type.lower()
            abatement_factor = LEVER_ABATEMENT_FACTORS.get(applied.lever_id, Decimal("0.50"))

            # Find matching activity rows for this lever
            has_kw_match = matching_calcs_found(target_kw, current_rows)
            matching_calcs = [
                calc
                for calc, act in current_rows
                if target_kw in act.activity_type.lower()
                or (act.ghg_category and target_kw in act.ghg_category.lower())
                or (act.scope == lever_def.target_scope and not has_kw_match)
            ]

            lever_baseline = sum((c.result_tco2e for c in matching_calcs), Decimal("0"))
            rate = Decimal(str(applied.implementation_rate))
            abated_tco2e = lever_baseline * rate * abatement_factor
            simulated_tco2e = lever_baseline - abated_tco2e

            # Economics: Annualized CapEx (10-year amortization = 10%) + Annual OpEx Delta
            capex = Decimal(
                str(
                    applied.custom_capex_usd
                    if applied.custom_capex_usd is not None
                    else lever_def.default_capex_usd
                )
            )
            opex = Decimal(
                str(
                    applied.custom_annual_opex_delta_usd
                    if applied.custom_annual_opex_delta_usd is not None
                    else lever_def.default_annual_opex_delta_usd
                )
            )
            annual_cost = (capex * Decimal("0.10")) + opex

            # Marginal Abatement Cost ($/tCO2e) = Annualized Cost / Abated tCO2e
            if abated_tco2e > Decimal("0"):
                mac = float(annual_cost / abated_tco2e)
            else:
                mac = 0.0

            red_pct = (
                float((abated_tco2e / lever_baseline) * Decimal("100"))
                if lever_baseline > Decimal("0")
                else 0.0
            )

            raw_impacts.append({
                "lever_id": applied.lever_id,
                "title": lever_def.title,
                "scope": lever_def.target_scope,
                "baseline_emissions_tco2e": float(lever_baseline),
                "simulated_emissions_tco2e": float(simulated_tco2e),
                "reduction_tco2e": float(abated_tco2e),
                "reduction_percent": round(red_pct, 2),
                "annualized_net_cost_usd": float(annual_cost),
                "mac": round(mac, 2),
            })

            total_abated += abated_tco2e
            total_annual_cost += annual_cost

        # 3. Sort by Marginal Abatement Cost ascending (MACC ROI curve: negative costs first)
        raw_impacts.sort(key=lambda x: x["mac"])

        ranked_results: list[LeverImpactResult] = []
        for rank, imp in enumerate(raw_impacts, start=1):
            ranked_results.append(
                LeverImpactResult(
                    lever_id=imp["lever_id"],
                    title=imp["title"],
                    scope=imp["scope"],
                    baseline_emissions_tco2e=imp["baseline_emissions_tco2e"],
                    simulated_emissions_tco2e=imp["simulated_emissions_tco2e"],
                    reduction_tco2e=imp["reduction_tco2e"],
                    reduction_percent=imp["reduction_percent"],
                    annualized_net_cost_usd=imp["annualized_net_cost_usd"],
                    marginal_abatement_cost_usd_per_tco2e=imp["mac"],
                    roi_rank=rank,
                )
            )

        simulated_gross = baseline_gross - total_abated
        total_red_pct = (
            float((total_abated / baseline_gross) * Decimal("100"))
            if baseline_gross > Decimal("0")
            else 0.0
        )

        target_met = None
        if request.target_reduction_percent is not None:
            target_met = total_red_pct >= request.target_reduction_percent

        return SimulationResponse(
            entity_id=request.entity_id,
            reporting_period=request.reporting_period,
            baseline_gross_tco2e=float(baseline_gross),
            simulated_gross_tco2e=float(simulated_gross),
            total_reduction_tco2e=float(total_abated),
            total_reduction_percent=round(total_red_pct, 2),
            net_annual_cost_usd=float(total_annual_cost),
            target_met=target_met,
            ranked_levers=ranked_results,
        )


def matching_calcs_found(keyword: str, rows: list[tuple[Calculation, ActivityData]]) -> bool:
    """Helper to check if any activity explicitly matches keyword."""
    return any(keyword in act.activity_type.lower() for _, act in rows)
