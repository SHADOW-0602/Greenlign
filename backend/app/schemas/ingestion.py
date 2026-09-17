"""Pydantic schemas for Ingestion API."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceDocumentRead(BaseModel):
    """Schema for returning source document metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int
    file_hash_sha256: str
    storage_path: str
    status: str
    error_message: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    processed_at: datetime | None = None


class ActivityDataRead(BaseModel):
    """Schema for activity data item output."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_document_id: uuid.UUID | None
    raw_line_ref: str
    entity_id: uuid.UUID
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


class DocumentUploadResponse(BaseModel):
    """Response returned after uploading a document."""

    document: SourceDocumentRead
    activities_count: int = 0
    task_id: str | None = None
    message: str


class DocumentDetailResponse(BaseModel):
    """Detailed response for a single source document including extracted line items."""

    document: SourceDocumentRead
    activities: list[ActivityDataRead]
