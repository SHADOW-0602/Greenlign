"""Pydantic schemas for audit trail and provenance endpoints."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditSourceDocumentSummary(BaseModel):
    """Source document summary in audit provenance chain."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int
    file_hash_sha256: str
    storage_path: str
    created_at: datetime


class AuditActivityDataSummary(BaseModel):
    """Activity data summary in audit provenance chain."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_line_ref: str
    supplier_ref: str
    activity_type: str
    quantity: Decimal
    unit: str
    geography: str
    period_start: date
    period_end: date
    scope: int | None = None
    ghg_category: str | None = None
    classification_confidence: float | None = None
    status: str


class AuditEmissionFactorSummary(BaseModel):
    """Emission factor summary in audit provenance chain."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    source_version: str
    activity_type: str
    geography: str
    unit: str
    factor_value: Decimal
    factor_unit: str
    published_date: date
    effective_from: date
    effective_to: date | None = None


class AuditCalculationSummary(BaseModel):
    """Calculation summary in audit provenance chain."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_data_id: uuid.UUID
    emission_factor_id: uuid.UUID
    formula_applied: str
    result_tco2e: Decimal
    computed_by: str
    computed_at: datetime


class AuditLogEntryResponse(BaseModel):
    """Single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    actor: str
    timestamp: datetime
    detail: dict[str, Any]


class AuditDisclosureSummary(BaseModel):
    """Disclosure referencing the calculation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    framework: str
    reporting_period: str
    status: str


class AuditTraceResponse(BaseModel):
    """Full end-to-end audit provenance chain for a calculation."""

    calculation: AuditCalculationSummary
    activity: AuditActivityDataSummary
    source_document: AuditSourceDocumentSummary | None = None
    emission_factor: AuditEmissionFactorSummary
    audit_events: list[AuditLogEntryResponse] = Field(default_factory=list)
    linked_disclosures: list[AuditDisclosureSummary] = Field(default_factory=list)


class ReferentialIntegrityCheckResponse(BaseModel):
    """Response when checking or guarding deletion."""

    can_delete: bool
    reason: str | None = None
    blocking_disclosures: list[uuid.UUID] = Field(default_factory=list)
