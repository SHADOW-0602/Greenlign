"""Classification and Review Queue API Endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.activity_data import ActivityData
from app.schemas.classification import (
    BatchClassifyRequest,
    BatchClassifyResponse,
    HumanReviewRequest,
    HumanReviewResponse,
    ReviewQueueItemResponse,
)
from app.services.classification_service import ClassificationService

router = APIRouter()


@router.get(
    "/queue",
    response_model=list[ReviewQueueItemResponse],
    status_code=status.HTTP_200_OK,
)
async def get_review_queue(
    entity_id: uuid.UUID | None = Query(None, description="Filter by reporting entity ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewQueueItemResponse]:
    """Retrieve activity data rows awaiting human review (< 0.75 confidence)."""
    stmt = (
        select(ActivityData)
        .where(ActivityData.status == "pending_review")
        .order_by(ActivityData.created_at.desc())
    )
    if entity_id:
        stmt = stmt.where(ActivityData.entity_id == entity_id)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    records = list(result.scalars().all())
    return [ReviewQueueItemResponse.model_validate(r) for r in records]


@router.post(
    "/review/{activity_id}",
    response_model=HumanReviewResponse,
    status_code=status.HTTP_200_OK,
)
async def apply_review(
    activity_id: uuid.UUID,
    payload: HumanReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> HumanReviewResponse:
    """Approve or override the classification for an activity record."""
    service = ClassificationService()
    try:
        updated = await service.apply_human_review(
            session=db,
            activity_id=activity_id,
            reviewer_id=payload.reviewer_id,
            scope=payload.scope,
            ghg_category=payload.ghg_category,
            notes=payload.notes,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=err_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg
        )

    return HumanReviewResponse(
        status="success",
        activity=ReviewQueueItemResponse.model_validate(updated),
    )


@router.post(
    "/batch-classify",
    response_model=BatchClassifyResponse,
    status_code=status.HTTP_200_OK,
)
async def batch_classify_activities(
    payload: BatchClassifyRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchClassifyResponse:
    """Run scope classification on pending activities."""
    service = ClassificationService()
    classified = await service.batch_classify(
        session=db,
        entity_id=payload.entity_id,
        document_id=payload.document_id,
        limit=payload.limit,
    )

    classified_count = sum(1 for a in classified if a.status == "classified")
    pending_review_count = sum(1 for a in classified if a.status == "pending_review")

    return BatchClassifyResponse(
        total_processed=len(classified),
        classified_count=classified_count,
        pending_review_count=pending_review_count,
        items=[ReviewQueueItemResponse.model_validate(a) for a in classified],
    )
