"""API router for regulatory disclosure reports and eligibility assessments."""

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.calculation import Calculation
from app.models.disclosure import Disclosure
from app.schemas.disclosure import (
    DisclosureDetailResponse,
    EntityEligibilityRequest,
    EntityEligibilityResponse,
    GenerateDisclosureRequest,
)
from app.services.disclosure_generator import DisclosureGenerator
from app.services.eligibility_checker import EligibilityChecker, IneligibleFrameworkError

router = APIRouter()


@router.post(
    "/check-eligibility",
    response_model=EntityEligibilityResponse,
    summary="Check entity eligibility across CA SB 253, CSRD, and GHG Protocol",
)
async def check_eligibility_endpoint(
    payload: EntityEligibilityRequest,
) -> EntityEligibilityResponse:
    """Evaluate entity profile parameters against statutory and voluntary frameworks."""
    return EligibilityChecker.check_all(payload)


@router.post(
    "/generate",
    response_model=DisclosureDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate regulatory disclosure report with audit citations",
)
async def generate_disclosure_endpoint(
    payload: GenerateDisclosureRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DisclosureDetailResponse:
    """Aggregate calculations, validate eligibility, persist Disclosure, and create PDF report."""
    generator = DisclosureGenerator(session)
    try:
        detail, _ = await generator.generate_disclosure(
            entity_id=payload.entity_id,
            framework=payload.framework,
            reporting_period=payload.reporting_period,
            entity_profile=payload.entity_profile,
            actor="api_user",
        )
        return detail
    except IneligibleFrameworkError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate disclosure: {e}",
        )


@router.get(
    "",
    response_model=list[DisclosureDetailResponse],
    summary="List disclosures for an entity",
)
async def list_disclosures_endpoint(
    session: Annotated[AsyncSession, Depends(get_db)],
    entity_id: uuid.UUID | None = Query(None, description="Filter by entity UUID"),
    framework: str | None = Query(None, description="Filter by framework"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[DisclosureDetailResponse]:
    """Retrieve existing disclosures."""
    query = select(Disclosure).order_by(Disclosure.id.desc())
    if entity_id:
        query = query.where(Disclosure.entity_id == entity_id)
    if framework:
        query = query.where(Disclosure.framework == framework)
    query = query.offset(offset).limit(limit)

    result = await session.scalars(query)
    disclosures = list(result.all())

    # Build response details for each
    responses: list[DisclosureDetailResponse] = []

    for d in disclosures:
        # Re-aggregate calculation totals
        calcs_res = await session.scalars(
            select(Calculation).where(Calculation.id.in_(d.line_item_refs or []))
        )
        calcs = list(calcs_res.all())
        total = sum((c.result_tco2e for c in calcs), Decimal("0"))

        responses.append(
            DisclosureDetailResponse(
                id=d.id,
                entity_id=d.entity_id,
                framework=d.framework,
                reporting_period=d.reporting_period,
                status=d.status,
                generated_document_ref=d.generated_document_ref,
                total_tco2e=total,
                scope_1_tco2e=Decimal("0"),
                scope_2_tco2e=Decimal("0"),
                scope_3_tco2e=Decimal("0"),
                scope_breakdown=[],
                line_item_refs=d.line_item_refs or [],
            )
        )
    return responses


@router.get(
    "/{id}/download-pdf",
    summary="Download generated PDF disclosure report with audit citations",
)
async def download_disclosure_pdf_endpoint(
    id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Dynamically render or stream the audit-cited PDF disclosure report."""
    disclosure = await session.get(Disclosure, id)
    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disclosure with ID '{id}' not found.",
        )

    generator = DisclosureGenerator(session)
    _, pdf_bytes = await generator.generate_disclosure(
        entity_id=disclosure.entity_id,
        framework=disclosure.framework,  # type: ignore[arg-type]
        reporting_period=disclosure.reporting_period,
        entity_profile=None,
    )

    filename = f"{disclosure.framework}_{disclosure.reporting_period}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
