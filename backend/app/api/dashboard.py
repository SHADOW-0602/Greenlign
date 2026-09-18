"""REST API Router for Executive ESG Analytics Dashboard."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    entity_id: UUID = Query(..., description="Target company/entity UUID"),
    reporting_period: str = Query(
        default="2025", description="Reporting period (e.g. '2025' or '2024')"
    ),
    session: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    """Retrieve aggregate emissions, Scope 1/2/3 breakdown, hotspots, and active anomaly flags."""
    service = DashboardService(session)
    return await service.get_dashboard_summary(
        entity_id=entity_id, reporting_period=reporting_period
    )
