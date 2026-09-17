from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "greenlign",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[],  # task modules registered in Phase 1+
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
