"""Tests for Celery calculation worker tasks."""

import uuid
from unittest.mock import AsyncMock, patch

from app.workers.calculation_tasks import calculate_document_emissions_task
from app.workers.celery_app import celery_app


def test_calculation_task_is_registered() -> None:
    """Verify calculate_document_emissions_task is properly registered in celery_app."""
    task_name = "app.workers.calculation_tasks.calculate_document_emissions_task"
    assert task_name in celery_app.tasks


def test_calculate_document_emissions_task_execution() -> None:
    """Test task executes and calls compute_document_activities."""
    doc_id = uuid.uuid4()
    mock_summary = {
        "computed": [
            {
                "activity_id": str(uuid.uuid4()),
                "calculation_id": str(uuid.uuid4()),
                "result_tco2e": "0.38590000",
            }
        ],
        "pending_factor": [],
        "errors": [],
    }

    with patch("app.workers.calculation_tasks.CalculationService") as mock_service_cls:
        mock_instance = AsyncMock()
        mock_instance.compute_document_activities.return_value = mock_summary
        mock_service_cls.return_value = mock_instance

        result = calculate_document_emissions_task(str(doc_id))

        assert result["status"] == "completed"
        assert result["computed_count"] == 1
        assert result["pending_factor_count"] == 0
        assert result["error_count"] == 0
        mock_instance.compute_document_activities.assert_awaited_once_with(
            source_document_id=doc_id,
            actor="celery_worker",
        )
