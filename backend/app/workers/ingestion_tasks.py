"""Celery tasks for async document ingestion processing."""

import asyncio
import uuid
from typing import Any

from app.core.database import AsyncSessionLocal
from app.services.ingestion_service import IngestionService
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.ingestion_tasks.process_document_task")
def process_document_task(source_document_id_str: str) -> dict[str, Any]:
    """Execute document processing asynchronously in worker."""
    doc_uuid = uuid.UUID(source_document_id_str)

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            service = IngestionService()
            activities = await service.process_document(
                session=session, source_document_id=doc_uuid
            )
            return {
                "source_document_id": source_document_id_str,
                "status": "completed",
                "rows_created": len(activities),
            }

    return asyncio.run(_run())
