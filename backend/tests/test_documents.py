from unittest.mock import patch
import io

def test_get_documents_unauthorized(client):
    response = client.get("/api/v1/documents/")
    assert response.status_code == 401

@patch("app.api.routes.documents.process_document_ingestion.delay")
def test_upload_document(mock_celery_task, client):
    # Register & Login
    client.post(
        "/api/v1/users/",
        json={"email": "uploader@enterprise.com", "password": "UploadPassword123!", "full_name": "Uploader User"}
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "uploader@enterprise.com", "password": "UploadPassword123!"}
    )
    token = login_response.json()["access_token"]
    
    # Upload Mock File
    file_content = b"This is a sample document for testing the ingestion flow."
    file_io = io.BytesIO(file_content)
    
    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("sample.txt", file_io, "text/plain")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "processing"
    assert data["filename"] == "sample.txt"
    
    # Ensure Celery task was dispatched with document ID
    mock_celery_task.assert_called_once_with(data["id"])
