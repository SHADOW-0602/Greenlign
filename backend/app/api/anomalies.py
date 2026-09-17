"""API router for anomaly detection, statistical outlier scans, and greenwashing checks."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.anomaly_flag import AnomalyFlag
from app.models.audit_log import AuditLogEntry
from app.schemas.anomaly import (
    AnomalyFlagResponse,
    AnomalyScanRequest,
    AnomalyScanSummary,
    NarrativeCheckRequest,
    NarrativeCheckResponse,
    ResolveAnomalyRequest,
)
from app.services.anomaly_detector import AnomalyDetector

router = APIRouter()


@router.post(
    "/scan",
    response_model=AnomalyScanSummary,
    summary="Run statistical, intensity outlier, and completeness anomaly scan",
)
async def scan_anomalies_endpoint(
    payload: AnomalyScanRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AnomalyScanSummary:
    """Execute statistical and scope completeness anomaly scan for an entity inventory."""
    detector = AnomalyDetector(session)
    flags = await detector.run_statistical_scan(
        entity_id=payload.entity_id,
        current_period=payload.current_period,
        baseline_period=payload.baseline_period,
        yoy_threshold_pct=payload.yoy_threshold_pct,
        zscore_threshold=payload.zscore_threshold,
    )
    flag_responses = [AnomalyFlagResponse.model_validate(f) for f in flags]
    return AnomalyScanSummary(
        entity_id=payload.entity_id,
        current_period=payload.current_period,
        baseline_period=payload.baseline_period,
        flags_detected_count=len(flags),
        flags=flag_responses,
    )


@router.post(
    "/check-narrative",
    response_model=NarrativeCheckResponse,
    summary="Evaluate sustainability narrative against verified calculation records",
)
async def check_narrative_endpoint(
    payload: NarrativeCheckRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NarrativeCheckResponse:
    """Cross-examine corporate claims against database calculations for greenwashing detection."""
    detector = AnomalyDetector(session)
    return await detector.evaluate_narrative_claims(
        entity_id=payload.entity_id,
        reporting_period=payload.reporting_period,
        narrative_text=payload.narrative_text,
        baseline_period=payload.baseline_period,
    )


@router.get(
    "",
    response_model=list[AnomalyFlagResponse],
    summary="List detected anomaly flags with optional filters",
)
async def list_anomalies_endpoint(
    session: Annotated[AsyncSession, Depends(get_db)],
    entity_id: uuid.UUID | None = Query(None, description="Filter by entity UUID"),
    reporting_period: str | None = Query(None, description="Filter by reporting period"),
    status_filter: str | None = Query(None, alias="status", description="Filter by flag status"),
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AnomalyFlagResponse]:
    """Retrieve anomaly flags from database."""
    query = select(AnomalyFlag).order_by(AnomalyFlag.created_at.desc())
    if entity_id:
        query = query.where(AnomalyFlag.entity_id == entity_id)
    if reporting_period:
        query = query.where(AnomalyFlag.reporting_period == reporting_period)
    if status_filter:
        query = query.where(AnomalyFlag.status == status_filter)
    if severity:
        query = query.where(AnomalyFlag.severity == severity)
    query = query.offset(offset).limit(limit)

    res = await session.scalars(query)
    flags = list(res.all())
    return [AnomalyFlagResponse.model_validate(f) for f in flags]


@router.patch(
    "/{id}/resolve",
    response_model=AnomalyFlagResponse,
    summary="Resolve an anomaly flag (confirm as issue or dismiss with reasoning)",
)
async def resolve_anomaly_endpoint(
    id: uuid.UUID,
    payload: ResolveAnomalyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AnomalyFlagResponse:
    """Update resolution status of an anomaly flag and write audit log entry."""
    flag = await session.get(AnomalyFlag, id)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly flag with ID '{id}' not found.",
        )

    flag.status = payload.status
    flag.resolution_notes = payload.notes
    flag.resolved_by = payload.actor
    flag.resolved_at = datetime.now()

    audit = AuditLogEntry(
        entity_type="anomaly_flag",
        entity_id=flag.id,
        action="RESOLVE_ANOMALY",
        actor=payload.actor,
        detail={
            "status": payload.status,
            "notes": payload.notes,
        },
    )
    session.add(audit)
    await session.commit()
    await session.refresh(flag)

    return AnomalyFlagResponse.model_validate(flag)
