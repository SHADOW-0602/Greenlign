"""REST API Router for Scope 3 Supplier Outreach Agent."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.outreach import (
    CreateOutreachRequest,
    GenerateEmailRequest,
    GenerateEmailResponse,
    MissingScope3SupplierItem,
    RecordSupplierResponseRequest,
    SupplierOutreachResponse,
)
from app.services.supplier_outreach import SupplierOutreachService

router = APIRouter()


@router.post("/generate-email", response_model=GenerateEmailResponse)
async def generate_supplier_email(
    request: GenerateEmailRequest,
    session: AsyncSession = Depends(get_db),
) -> GenerateEmailResponse:
    """Draft tailored ESG primary data inquiry using Groq LLM with fallback."""
    service = SupplierOutreachService(session)
    return await service.generate_email(request)


@router.get("/missing-scope3", response_model=list[MissingScope3SupplierItem])
async def get_missing_scope3_suppliers(
    entity_id: UUID = Query(..., description="Corporate entity UUID"),
    reporting_period: str = Query(default="2025", description="Reporting period"),
    session: AsyncSession = Depends(get_db),
) -> list[MissingScope3SupplierItem]:
    """Retrieve Scope 3 categories and suppliers relying on secondary proxy factors."""
    service = SupplierOutreachService(session)
    return await service.find_missing_scope3_suppliers(
        entity_id=entity_id, reporting_period=reporting_period
    )


@router.post("", response_model=SupplierOutreachResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier_outreach(
    request: CreateOutreachRequest,
    session: AsyncSession = Depends(get_db),
) -> SupplierOutreachResponse:
    """Create a new supplier outreach inquiry record."""
    service = SupplierOutreachService(session)
    outreach = await service.create_outreach(request)
    return SupplierOutreachResponse.model_validate(outreach)


@router.get("", response_model=list[SupplierOutreachResponse])
async def list_supplier_outreach(
    entity_id: UUID = Query(..., description="Corporate entity UUID"),
    status: str | None = Query(default=None, description="Optional status filter"),
    session: AsyncSession = Depends(get_db),
) -> list[SupplierOutreachResponse]:
    """List all outreach communications for an entity."""
    service = SupplierOutreachService(session)
    items = await service.list_outreach(entity_id=entity_id, status=status)
    return [SupplierOutreachResponse.model_validate(item) for item in items]


@router.post("/{outreach_id}/send", response_model=SupplierOutreachResponse)
async def send_supplier_outreach(
    outreach_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> SupplierOutreachResponse:
    """Dispatch supplier outreach communication and mark status as SENT."""
    service = SupplierOutreachService(session)
    try:
        outreach = await service.send_outreach(outreach_id)
        return SupplierOutreachResponse.model_validate(outreach)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.patch("/{outreach_id}/record-response", response_model=SupplierOutreachResponse)
async def record_supplier_response(
    outreach_id: UUID,
    request: RecordSupplierResponseRequest,
    session: AsyncSession = Depends(get_db),
) -> SupplierOutreachResponse:
    """Record verified primary supplier emission factor and consumption quantities."""
    service = SupplierOutreachService(session)
    try:
        outreach = await service.record_response(outreach_id, request)
        return SupplierOutreachResponse.model_validate(outreach)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
