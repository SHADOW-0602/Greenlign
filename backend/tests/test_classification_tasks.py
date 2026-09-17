"""Tests for Celery classification background worker tasks."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.celery_app import celery_app
from app.workers.classification_tasks import classify_document_activities_task


def test_celery_task_registration() -> None:
    """Verify classification task is registered with celery_app."""
    task_name = "app.workers.classification_tasks.classify_document_activities_task"
    assert task_name in celery_app.tasks


def test_classify_document_activities_task_execution() -> None:
    """Verify synchronous invocation of Celery task calls ClassificationService."""
    doc_id = uuid.uuid4()
    mock_act1 = MagicMock()
    mock_act1.status = "classified"
    mock_act2 = MagicMock()
    mock_act2.status = "pending_review"
    mock_activities = [mock_act1, mock_act2]

    with patch(
        "app.workers.classification_tasks.ClassificationService"
    ) as mock_service_cls:
        mock_instance = mock_service_cls.return_value
        mock_instance.batch_classify = AsyncMock(return_value=mock_activities)

        res = classify_document_activities_task(str(doc_id))

        assert res["status"] == "completed"
        assert res["source_document_id"] == str(doc_id)
        assert res["total_processed"] == 2
        assert res["classified_count"] == 1
        assert res["pending_review_count"] == 1
        mock_instance.batch_classify.assert_awaited_once()
