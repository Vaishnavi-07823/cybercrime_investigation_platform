from celery import Celery

from app.core.config import get_settings


settings = get_settings()
celery_app = Celery(
    "cybercrime_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="platform.ping")
def ping() -> dict:
    return {"status": "ok"}
