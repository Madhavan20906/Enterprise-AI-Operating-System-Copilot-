from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import Any, List
from app.api.deps import SessionDep, get_current_active_user
from app.db.models import User, Document
from app.infrastructure.tasks import process_document_ingestion
from app.infrastructure.qdrant import qdrant_rag
import os

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Maximum file size: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg"}

@router.post("/upload")
async def upload_document(
    db: SessionDep,
    current_user: User = Depends(get_current_active_user),
    file: UploadFile = File(...),
) -> Any:
    """
    Upload a new document for ingestion into the enterprise operating system.
    Supports PDF, DOCX, PPTX, XLSX, CSV, Images, TXT, and MD files up to 50 MB.
    Ingestion runs asynchronously in the background via Celery queue worker.
    """
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) / (1024*1024):.1f} MB). Maximum allowed: {MAX_FILE_SIZE / (1024*1024):.0f} MB"
        )
    
    # Save to disk
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(content)
        
    doc = Document(
        filename=file.filename,
        file_path=file_path,
        uploaded_by_id=current_user.id,
        status="processing",
        department=getattr(current_user, "department", "general")
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Dispatch asynchronous ingestion task to Celery queue worker
    process_document_ingestion.delay(doc.id)
    
    return {
        "message": "File uploaded successfully. Processing started in background.",
        "id": doc.id,
        "status": doc.status,
        "filename": doc.filename
    }

@router.get("/")
def get_documents(
    db: SessionDep,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get all documents. Simple RBAC: admin sees all, others see own or department documents.
    """
    if current_user.role == "administrator":
        docs = db.query(Document).all()
    else:
        dept = getattr(current_user, "department", "general")
        docs = db.query(Document).filter(
            (Document.uploaded_by_id == current_user.id) | 
            (Document.department == dept)
        ).all()
    return docs

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: SessionDep,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete a document and clean up its vectors from Qdrant.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Simple ABAC/RBAC: Only owner or admin can delete
    if doc.uploaded_by_id != current_user.id and current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")
    
    # Delete from Qdrant vector database
    try:
        qdrant_rag.delete_document_points(doc.id)
    except Exception as e:
        # log warning but continue database cleanup
        pass
        
    # Remove file from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
    
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted and index purged successfully.", "id": document_id}
