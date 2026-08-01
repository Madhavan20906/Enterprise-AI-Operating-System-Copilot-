"""
Enterprise AI OS — Document Processing Tasks
Background tasks for document ingestion, parsing, OCR, and embedding.
"""
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.process_document", max_retries=3)
def process_document(self, document_id: int, file_path: str, file_type: str):
    """
    Background task: Parse, OCR (if needed), chunk, embed and index a document.
    """
    try:
        logger.info(f"[Task] Processing document {document_id} | type={file_type}")
        # Import here to avoid circular imports at module load time
        from app.infrastructure.database import SessionLocal
        from app.db.models import Document

        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.warning(f"[Task] Document {document_id} not found in DB.")
                return {"status": "not_found", "document_id": document_id}

            # TODO: plug in your actual parsing / embedding pipeline here
            # e.g. ingest_pipeline.run(file_path, doc)

            logger.info(f"[Task] Document {document_id} processed successfully.")
            return {"status": "success", "document_id": document_id}
        finally:
            db.close()

    except Exception as exc:
        logger.error(f"[Task] Error processing document {document_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="tasks.health_check")
def health_check():
    """Simple task to verify the worker is alive."""
    return {"status": "ok", "worker": "alive"}
