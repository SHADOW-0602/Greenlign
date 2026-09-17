from app.core.config import settings
from app.workers.celery_app import celery_app


def test_celery_app_importable_and_configured() -> None:
    """Celery app must be importable, named correctly, and configured."""
    assert celery_app.main == "greenlign"
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
    assert "json" in celery_app.conf.accept_content
    assert celery_app.conf.broker_url == settings.redis_url
    assert celery_app.conf.result_backend == settings.redis_url
