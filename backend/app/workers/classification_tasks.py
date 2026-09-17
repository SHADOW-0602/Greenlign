"""Celery tasks for async activity scope classification."""

import asyncio
import uuid
from typing import Any

from app.core.database import AsyncSessionLocal
from app.services.classification_service import ClassificationService
from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.classification_tasks.classify_document_activities_task"
)
def classify_document_activities_task(
    source_document_id_str: str,
) -> dict[str, Any]:
    """Execute activity classification for all line items in a document asynchronously."""
    doc_uuid = uuid.UUID(source_document_id_str)

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            service = ClassificationService()
            classified = await service.batch_classify(
                session=session, document_id=doc_uuid, limit=10000
            )
            classified_count = sum(1 for a in classified if a.status == "classified")
            pending_review_count = sum(
                1 for a in classified if a.status == "pending_review"
            )
            return {
                "source_document_id": source_document_id_str,
                "status": "completed",
                "total_processed": len(classified),
                "classified_count": classified_count,
                "pending_review_count": pending_review_count,
            }

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(lambda: asyncio.run(_run())).result()
    return asyncio.run(_run())
