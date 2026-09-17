"""Pydantic schemas for classification review queue and endpoints."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReviewQueueItemResponse(BaseModel):
    """Activity data item in review queue or classification response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_id: uuid.UUID
    source_document_id: uuid.UUID | None = None
    raw_line_ref: str
    activity_type: str
    quantity: Decimal
    unit: str
    geography: str
    period_start: date
    period_end: date
    supplier_ref: str
    scope: int | None = None
    ghg_category: str | None = None
    classification_confidence: float | None = None
    status: str
    created_at: datetime


class HumanReviewRequest(BaseModel):
    """Payload for reviewer overriding or approving activity classification."""

    scope: int = Field(..., ge=1, le=3, description="GHG Protocol Scope (1, 2, or 3)")
    ghg_category: str = Field(..., description="Valid GHG category for the given scope")
    reviewer_id: str = Field(..., min_length=1, description="Unique ID of human reviewer")
    notes: str | None = Field(None, description="Optional audit notes on review reason")


class HumanReviewResponse(BaseModel):
    """Response returned after human review override."""

    status: str = "success"
    activity: ReviewQueueItemResponse


class BatchClassifyRequest(BaseModel):
    """Request payload for on-demand batch classification."""

    entity_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    limit: int = Field(100, ge=1, le=1000)


class BatchClassifyResponse(BaseModel):
    """Summary of batch classification results."""

    total_processed: int
    classified_count: int
    pending_review_count: int
    items: list[ReviewQueueItemResponse]
