"""Executive ESG Dashboard Analytics Service.

Aggregates deterministic calculations across GHG Scopes 1, 2, and 3,
computes top emission hotspots, historical multi-year trends, and monitors
active audit anomaly flags.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.anomaly_flag import AnomalyFlag
from app.models.calculation import Calculation
from app.schemas.dashboard import (
    CategoryHotspot,
    DashboardSummaryResponse,
    PeriodicTrendPoint,
    ScopeMetric,
)


class DashboardService:
    """Service providing aggregate ESG KPIs and emission breakdowns."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_dashboard_summary(
        self, entity_id: UUID, reporting_period: str
    ) -> DashboardSummaryResponse:
        """Fetch and aggregate calculations, hotspots, trends, and flags for an entity."""
        # 1. Fetch all calculations and activity data for the entity
        query = (
            select(Calculation, ActivityData)
            .join(ActivityData, Calculation.activity_data_id == ActivityData.id)
            .where(ActivityData.entity_id == entity_id)
        )
        result = await self.session.execute(query)
        all_rows = list(result.all())

        # Filter for the requested reporting period
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
            if reporting_period in valid_periods or reporting_period == act_year:
                current_rows.append((calc, act))

        if not current_rows and all_rows:
            # Fallback if specific year filter didn't match
            current_rows = [(r[0], r[1]) for r in all_rows]

        # 2. Deterministic Scope aggregation using Decimal
        scope_totals: dict[int, Decimal] = {1: Decimal("0"), 2: Decimal("0"), 3: Decimal("0")}
        category_totals: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"tco2e": Decimal("0"), "count": 0, "scope": 3}
        )

        for calc, act in current_rows:
            sc = act.scope if act.scope in (1, 2, 3) else 3
            scope_totals[sc] += calc.result_tco2e

            cat = act.ghg_category or f"Scope {sc} Uncategorized"
            category_totals[cat]["tco2e"] += calc.result_tco2e
            category_totals[cat]["count"] += 1
            category_totals[cat]["scope"] = sc

        gross_tco2e = sum(scope_totals.values(), Decimal("0"))

        # 3. Scope metrics
        scope_breakdown: list[ScopeMetric] = []
        for s in (1, 2, 3):
            s_val = scope_totals[s]
            s_share = (
                float((s_val / gross_tco2e) * Decimal("100")) if gross_tco2e > Decimal("0") else 0.0
            )
            scope_breakdown.append(
                ScopeMetric(
                    scope=s,
                    total_tco2e=float(s_val),
                    share_percentage=round(s_share, 2),
                )
            )

        # 4. Top 5 Hotspots
        sorted_categories = sorted(
            category_totals.items(),
            key=lambda x: x[1]["tco2e"],
            reverse=True,
        )

        top_hotspots: list[CategoryHotspot] = []
        for cat_name, info in sorted_categories[:5]:
            cat_val = info["tco2e"]
            cat_share = (
                float((cat_val / gross_tco2e) * Decimal("100"))
                if gross_tco2e > Decimal("0")
                else 0.0
            )
            top_hotspots.append(
                CategoryHotspot(
                    ghg_category=cat_name,
                    scope=info["scope"],
                    total_tco2e=float(cat_val),
                    share_percentage=round(cat_share, 2),
                    activity_count=info["count"],
                )
            )

        # 5. Historical Trends
        period_trends: dict[str, dict[int, Decimal]] = defaultdict(
            lambda: {1: Decimal("0"), 2: Decimal("0"), 3: Decimal("0")}
        )
        for calc, act in all_rows:
            yr = str(act.period_start.year)
            sc = act.scope if act.scope in (1, 2, 3) else 3
            period_trends[yr][sc] += calc.result_tco2e

        historical_trends: list[PeriodicTrendPoint] = []
        for yr in sorted(period_trends.keys()):
            sc_map = period_trends[yr]
            s1, s2, s3 = sc_map[1], sc_map[2], sc_map[3]
            historical_trends.append(
                PeriodicTrendPoint(
                    reporting_period=yr,
                    scope1_tco2e=float(s1),
                    scope2_tco2e=float(s2),
                    scope3_tco2e=float(s3),
                    total_tco2e=float(s1 + s2 + s3),
                )
            )

        # 6. Anomaly Counts
        flags_query = (
            select(
                func.count(AnomalyFlag.id).label("total_open"),
                func.count(AnomalyFlag.id)
                .filter(AnomalyFlag.severity == "CRITICAL")
                .label("critical_open"),
            )
            .where(
                AnomalyFlag.entity_id == entity_id,
                AnomalyFlag.status == "OPEN",
            )
        )
        flag_res = await self.session.execute(flags_query)
        open_count, crit_count = flag_res.one()

        return DashboardSummaryResponse(
            entity_id=entity_id,
            reporting_period=reporting_period,
            gross_emissions_tco2e=float(gross_tco2e),
            scope_breakdown=scope_breakdown,
            top_hotspots=top_hotspots,
            historical_trends=historical_trends,
            total_calculations=len(current_rows),
            open_anomalies_count=int(open_count or 0),
            critical_anomalies_count=int(crit_count or 0),
        )
