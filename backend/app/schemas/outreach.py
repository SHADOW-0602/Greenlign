from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerateEmailRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    supplier_name: str = Field(..., description="Legal or display name of the supplier")
    supplier_ref: str = Field(..., description="Tokenized or internal supplier ID")
    activity_type: str = Field(..., description="Type of goods or services procured")
    reporting_period: str = Field(default="2025", description="Reporting year")
    template_type: str = Field(
        default="PRIMARY_EMISSION_FACTOR",
        description="PRIMARY_EMISSION_FACTOR | ACTIVITY_DATA_VERIFICATION | REDUCTION_PLEDGE",
    )


class GenerateEmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_type: str
    subject: str
    body: str


class CreateOutreachRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: UUID
    supplier_ref: str
    supplier_name: str | None = None
    supplier_email: str
    contact_name: str
    activity_type: str
    reporting_period: str
    template_type: str = "PRIMARY_EMISSION_FACTOR"
    custom_subject: str | None = None
    custom_body: str | None = None


class SupplierOutreachResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_id: UUID
    supplier_ref: str
    supplier_name: str | None
    supplier_email: str
    contact_name: str
    activity_type: str
    reporting_period: str
    status: str
    template_type: str
    generated_email_subject: str
    generated_email_body: str
    response_data_json: dict[str, Any]
    sent_at: datetime | None
    responded_at: datetime | None
    created_at: datetime


class RecordSupplierResponseRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    primary_factor_value: float | None = Field(
        default=None, description="Supplier-provided primary emission intensity"
    )
    primary_factor_unit: str | None = Field(
        default=None, description="e.g. kgCO2e/kg, kgCO2e/unit, kgCO2e/t-km"
    )
    verified_quantity: float | None = Field(
        default=None, description="Verified consumption or purchase amount"
    )
    response_notes: str | None = Field(
        default=None, description="Explanatory notes or audit comments"
    )


class MissingScope3SupplierItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    supplier_ref: str
    activity_type: str
    reporting_period: str
    current_factor_source: str
    estimated_tco2e: float
    line_item_count: int
