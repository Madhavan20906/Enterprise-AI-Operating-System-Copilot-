"""
Enterprise AI OS — Celery Application
Async task queue for document ingestion, OCR, and background processing.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "enterprise_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.document_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

if __name__ == "__main__":
    celery_app.start()
