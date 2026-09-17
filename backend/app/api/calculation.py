"""API router for greenhouse gas emission calculations."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.calculation import Calculation
from app.schemas.calculation import (
    BatchComputeRequest,
    BatchComputeResponse,
    CalculationResponse,
)
from app.services.calculation_service import CalculationService

router = APIRouter()


@router.post(
    "/compute/{activity_id}",
    response_model=CalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute emissions for a single activity data line item",
)
async def compute_activity_endpoint(
    activity_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Calculation:
    """Run deterministic emission calculation for a single activity record."""
    service = CalculationService(session)
    try:
        calc = await service.compute_activity(activity_id, actor="api_user")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Calculation error: {e}",
        )

    if not calc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No matching emission factor found; activity flagged pending_factor.",
        )

    return calc


@router.post(
    "/batch-compute",
    response_model=BatchComputeResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute emissions for a batch of activities or a document",
)
async def batch_compute_endpoint(
    payload: BatchComputeRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BatchComputeResponse:
    """Run calculation on multiple activities."""
    service = CalculationService(session)
    calculations: list[Calculation] = []
    pending_factor_count = 0
    error_count = 0

    if payload.source_document_id:
        summary = await service.compute_document_activities(
            source_document_id=payload.source_document_id,
            actor="api_batch",
        )
        calc_ids = [uuid.UUID(c["calculation_id"]) for c in summary["computed"]]
        if calc_ids:
            res = await session.scalars(
                select(Calculation).where(Calculation.id.in_(calc_ids))
            )
            calculations = list(res.all())
        pending_factor_count = len(summary["pending_factor"])
        error_count = len(summary["errors"])

    elif payload.activity_ids:
        for act_id in payload.activity_ids:
            try:
                c = await service.compute_activity(act_id, actor="api_batch")
                if c:
                    calculations.append(c)
                else:
                    pending_factor_count += 1
            except Exception:
                error_count += 1
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either source_document_id or activity_ids must be provided.",
        )

    calc_responses = [CalculationResponse.model_validate(c) for c in calculations]

    return BatchComputeResponse(
        computed_count=len(calculations),
        pending_factor_count=pending_factor_count,
        error_count=error_count,
        calculations=calc_responses,
    )


@router.get(
    "/{id}",
    response_model=CalculationResponse,
    summary="Get calculation by calculation ID",
)
async def get_calculation_by_id(
    id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Calculation:
    """Retrieve calculation record by its UUID."""
    calc = await session.get(Calculation, id)
    if not calc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation with ID {id} not found.",
        )
    return calc


@router.get(
    "/by-activity/{activity_id}",
    response_model=CalculationResponse,
    summary="Get calculation by activity data ID",
)
async def get_calculation_by_activity(
    activity_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Calculation:
    """Retrieve calculation record associated with a given activity."""
    res = await session.scalars(
        select(Calculation).where(Calculation.activity_data_id == activity_id)
    )
    calc = res.first()
    if not calc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No calculation found for activity ID {activity_id}.",
        )
    return calc
