"""Celery tasks for async greenhouse gas emission calculation."""

import asyncio
import concurrent.futures
import uuid
from typing import Any

from app.core.database import AsyncSessionLocal
from app.services.calculation_service import CalculationService
from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.calculation_tasks.calculate_document_emissions_task"
)
def calculate_document_emissions_task(
    source_document_id_str: str,
) -> dict[str, Any]:
    """Execute emission calculation for all activity line items in a document asynchronously."""
    doc_uuid = uuid.UUID(source_document_id_str)

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            service = CalculationService(session)
            summary = await service.compute_document_activities(
                source_document_id=doc_uuid,
                actor="celery_worker",
            )
            return {
                "source_document_id": source_document_id_str,
                "status": "completed",
                "computed_count": len(summary["computed"]),
                "pending_factor_count": len(summary["pending_factor"]),
                "error_count": len(summary["errors"]),
                "results": summary,
            }

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(lambda: asyncio.run(_run())).result()
    return asyncio.run(_run())
