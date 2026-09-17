"""API router for audit trail, provenance tracing, and referential integrity."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.audit import (
    AuditLogEntryResponse,
    AuditTraceResponse,
    ReferentialIntegrityCheckResponse,
)
from app.services.audit_service import AuditService, ReferentialIntegrityError

router = APIRouter()


@router.get(
    "/trace/{calculation_id}",
    response_model=AuditTraceResponse,
    summary="Get full end-to-end provenance trace for a calculation",
)
async def get_calculation_trace_endpoint(
    calculation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuditTraceResponse:
    """Retrieve complete provenance chain for a calculation in under 200ms."""
    service = AuditService(session)
    try:
        return await service.get_calculation_trace(calculation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audit trace: {e}",
        )


@router.get(
    "/logs",
    response_model=list[AuditLogEntryResponse],
    summary="Query audit log entries with optional filters",
)
async def get_audit_logs_endpoint(
    session: Annotated[AsyncSession, Depends(get_db)],
    entity_id: uuid.UUID | None = Query(None, description="Filter by entity UUID"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    action: str | None = Query(None, description="Filter by action code"),
    actor: str | None = Query(None, description="Filter by actor ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[AuditLogEntryResponse]:
    """Retrieve filterable audit log entries."""
    service = AuditService(session)
    entries = await service.list_audit_logs(
        entity_id=entity_id,
        entity_type=entity_type,
        action=action,
        actor=actor,
        limit=limit,
        offset=offset,
    )
    return [AuditLogEntryResponse.model_validate(e) for e in entries]


@router.get(
    "/check-calculation-deletable/{calculation_id}",
    response_model=ReferentialIntegrityCheckResponse,
    summary="Check if a calculation can be deleted without violating referential integrity",
)
async def check_calculation_deletable_endpoint(
    calculation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReferentialIntegrityCheckResponse:
    service = AuditService(session)
    return await service.check_calculation_deletable(calculation_id)


@router.delete(
    "/calculations/{calculation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a calculation record guarded by disclosure referential integrity",
)
async def delete_calculation_endpoint(
    calculation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    actor: str = Query("auditor_api", description="Actor identifier"),
) -> None:
    service = AuditService(session)
    try:
        await service.delete_calculation_guarded(calculation_id, actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReferentialIntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/emission-factors/{factor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an emission factor guarded by calculation referential integrity",
)
async def delete_emission_factor_endpoint(
    factor_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    actor: str = Query("admin_api", description="Actor identifier"),
) -> None:
    service = AuditService(session)
    try:
        await service.delete_emission_factor_guarded(factor_id, actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReferentialIntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
