"""Tests for Celery ingestion tasks."""
import uuid
from unittest.mock import AsyncMock, patch

from app.workers.celery_app import celery_app
from app.workers.ingestion_tasks import process_document_task


def test_process_document_task_registered():
    """Verify task is registered under its explicit task name."""
    task_name = "app.workers.ingestion_tasks.process_document_task"
    assert celery_app.tasks[task_name].name == process_document_task.name


def test_process_document_task_execution():
    """Verify synchronous invocation of Celery task calls IngestionService."""
    doc_id = uuid.uuid4()
    mock_activities = [object(), object()]

    with patch("app.workers.ingestion_tasks.IngestionService") as mock_service_cls:
        mock_instance = mock_service_cls.return_value
        mock_instance.process_document = AsyncMock(return_value=mock_activities)

        res = process_document_task(str(doc_id))

        assert res["status"] == "completed"
        assert res["source_document_id"] == str(doc_id)
        assert res["rows_created"] == 2
        mock_instance.process_document.assert_awaited_once()
