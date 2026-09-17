"""Ingestion API Endpoints."""

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.activity_data import ActivityData
from app.models.source_document import SourceDocument
from app.schemas.ingestion import (
    ActivityDataRead,
    DocumentDetailResponse,
    DocumentUploadResponse,
    SourceDocumentRead,
)
from app.services.ingestion_service import (
    IngestionError,
    IngestionService,
    UnsupportedFileTypeError,
)
from app.workers.ingestion_tasks import process_document_task

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_200_OK)
async def upload_document(
    file: UploadFile = File(...),
    entity_id: uuid.UUID = Form(...),
    column_mapping: str | None = Form(None),
    async_process: bool = Form(False),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload an ERP export (CSV/XLSX) or utility bill PDF and normalize into ActivityData."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file has no filename."
        )

    # Parse optional column mapping JSON
    parsed_mapping: dict[str, str] | None = None
    if column_mapping:
        try:
            raw_parsed = json.loads(column_mapping)
            if not isinstance(raw_parsed, dict):
                raise ValueError("column_mapping must be a JSON object mapping keys to values.")
            parsed_mapping = {str(k): str(v) for k, v in raw_parsed.items()}
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid column_mapping JSON: {exc}",
            )

    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        )

    service = IngestionService()

    try:
        if async_process:
            source_doc = await service.ingest_document(
                session=db,
                entity_id=entity_id,
                filename=file.filename,
                content=content,
                column_mapping=parsed_mapping,
            )
            # Enqueue to Celery
            task_result = process_document_task.delay(str(source_doc.id))
            return DocumentUploadResponse(
                document=SourceDocumentRead.model_validate(source_doc),
                activities_count=0,
                task_id=task_result.id,
                message="File uploaded successfully. Background processing started.",
            )
        else:
            source_doc, activities = await service.ingest_and_process_document(
                session=db,
                entity_id=entity_id,
                filename=file.filename,
                content=content,
                column_mapping=parsed_mapping,
            )
            return DocumentUploadResponse(
                document=SourceDocumentRead.model_validate(source_doc),
                activities_count=len(activities),
                task_id=None,
                message=(
                    "File uploaded and processed successfully. "
                    f"Created {len(activities)} line items."
                ),
            )

    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion processing error: {exc}",
        )


@router.get("/documents", response_model=list[SourceDocumentRead])
async def list_documents(
    entity_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[SourceDocumentRead]:
    """List all source documents for a given entity."""
    query = (
        select(SourceDocument)
        .where(SourceDocument.entity_id == entity_id)
        .order_by(SourceDocument.created_at.desc())
    )
    result = await db.execute(query)
    docs = result.scalars().all()
    return [SourceDocumentRead.model_validate(d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_detail(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Retrieve details and extracted line items for a specific source document."""
    doc_res = await db.execute(
        select(SourceDocument).where(SourceDocument.id == document_id)
    )
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SourceDocument with ID {document_id} not found.",
        )

    act_res = await db.execute(
        select(ActivityData)
        .where(ActivityData.source_document_id == document_id)
        .order_by(ActivityData.created_at.asc())
    )
    activities = act_res.scalars().all()

    return DocumentDetailResponse(
        document=SourceDocumentRead.model_validate(doc),
        activities=[ActivityDataRead.model_validate(a) for a in activities],
    )
