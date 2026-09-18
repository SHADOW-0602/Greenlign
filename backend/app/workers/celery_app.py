from celery import Celery

from app.core.config import settings


def _get_celery_redis_url(raw_url: str) -> str:
    """Ensure TLS rediss:// URLs satisfy Celery backend SSL requirements."""
    if raw_url.startswith("rediss://") and "ssl_cert_reqs" not in raw_url:
        separator = "&" if "?" in raw_url else "?"
        return f"{raw_url}{separator}ssl_cert_reqs=CERT_REQUIRED"
    return raw_url


redis_url = _get_celery_redis_url(settings.redis_url)

celery_app = Celery(
    "greenlign",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.workers.ingestion_tasks",
        "app.workers.classification_tasks",
        "app.workers.calculation_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
