"""Pydantic schemas for calculation API endpoints."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CalculationResponse(BaseModel):
    """Output representation of a completed emission calculation record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_data_id: uuid.UUID
    emission_factor_id: uuid.UUID
    formula_applied: str
    result_tco2e: Decimal
    computed_by: str
    computed_at: datetime


class BatchComputeRequest(BaseModel):
    """Request payload to trigger calculations for a document or specific activities."""

    source_document_id: uuid.UUID | None = None
    activity_ids: list[uuid.UUID] | None = None


class BatchComputeResponse(BaseModel):
    """Summary of batch calculation run."""

    computed_count: int
    pending_factor_count: int
    error_count: int
    calculations: list[CalculationResponse]
