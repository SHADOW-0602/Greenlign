"""Pydantic schemas for anomaly detection and greenwashing narrative verification."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AnomalySeverity = Literal["CRITICAL", "WARNING", "INFO"]
AnomalyStatus = Literal["OPEN", "CONFIRMED", "DISMISSED"]
ClaimVerdict = Literal["SUPPORTED", "UNSUPPORTED", "POTENTIAL_GREENWASHING", "CONTRADICTED"]


class AnomalyScanRequest(BaseModel):
    """Request payload for triggering statistical and rule-based anomaly scan."""

    entity_id: uuid.UUID = Field(..., description="Target reporting entity UUID")
    current_period: str = Field(..., description="Current reporting period (e.g., '2025')")
    baseline_period: str | None = Field(
        None, description="Prior baseline period for comparison (e.g., '2024')"
    )
    yoy_threshold_pct: Decimal = Field(
        Decimal("50.0"),
        description="Percentage threshold for flagging unexplained YoY drop",
        ge=Decimal("1.0"),
        le=Decimal("100.0"),
    )
    zscore_threshold: float = Field(
        3.0,
        description="Z-score threshold for intensity outlier detection",
        ge=1.5,
        le=10.0,
    )


class AnomalyFlagResponse(BaseModel):
    """Details of a detected anomaly flag."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_id: uuid.UUID
    reporting_period: str
    flag_type: str
    severity: str
    title: str
    description: str
    status: str
    details_json: dict[str, Any]
    resolution_notes: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class AnomalyScanSummary(BaseModel):
    """Summary of an anomaly scan execution across an entity's inventory."""

    entity_id: uuid.UUID
    current_period: str
    baseline_period: str | None
    flags_detected_count: int
    flags: list[AnomalyFlagResponse]


class ResolveAnomalyRequest(BaseModel):
    """Request to resolve (confirm or dismiss) an anomaly flag."""

    status: Literal["CONFIRMED", "DISMISSED"]
    notes: str = Field(..., min_length=5, description="Auditor resolution rationale")
    actor: str = Field("auditor", description="Auditor username or identifier")


class NarrativeClaimFinding(BaseModel):
    """Cross-examination finding for a single empirical sustainability statement."""

    claim_text: str = Field(..., description="Specific claim extracted from narrative")
    verdict: ClaimVerdict = Field(..., description="Audit consistency verdict")
    claimed_metric: str = Field(..., description="Value claimed in narrative")
    actual_metric: str = Field(..., description="Actual value verified in calculation ledger")
    discrepancy_explanation: str = Field(..., description="Explanation of variance or consistency")


class NarrativeCheckRequest(BaseModel):
    """Request payload for cross-referencing corporate text against calculation records."""

    entity_id: uuid.UUID = Field(..., description="Entity UUID")
    reporting_period: str = Field(..., description="Reporting period evaluated")
    baseline_period: str | None = Field(
        None, description="Prior baseline period for trend comparison"
    )
    narrative_text: str = Field(
        ...,
        min_length=10,
        max_length=20000,
        description="Submitted report text, executive summary, or press release",
    )


class NarrativeCheckResponse(BaseModel):
    """Audit evaluation response for greenwashing and narrative consistency."""

    overall_status: Literal["CLEAN", "FLAGGED"]
    findings: list[NarrativeClaimFinding]
    flag_id: uuid.UUID | None = None
    summary_text: str
