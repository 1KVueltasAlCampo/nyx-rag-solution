import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Mock file content for upload tests
FAKE_PDF_CONTENT = (
    b"%PDF-1.7\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog /Pages 2 0 R >>\n"
    b"endobj\n"
    b"2 0 obj\n"
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
    b"endobj\n"
    b"3 0 obj\n"
    b"<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 600 800] >>\n"
    b"endobj\n"
    b"xref\n"
    b"0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000060 00000 n \n"
    b"0000000117 00000 n \n"
    b"trailer\n"
    b"<< /Size 4 /Root 1 0 R >>\n"
    b"startxref\n"
    b"205\n"
    b"%%EOF\n"
)

FAKE_FILENAME = "test_document.pdf"

def test_health_check():
    """1. Test that the system is alive."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "gemini" in data["components"]["llm"]

def test_upload_document_happy_path():
    """2. Test uploading a new document."""

    files = {"file": (FAKE_FILENAME, FAKE_PDF_CONTENT, "application/pdf")}
    response = client.post("/api/v1/documents", files=files)
    
    # It can be 200 (Processed) or 200 (Skipped) if tests were run before
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["processed", "skipped"]
    assert "doc_id" in data["data"]

def test_upload_incremental_ingestion():
    """3. Test that re-uploading the same file returns 'skipped'."""
    files = {"file": (FAKE_FILENAME, FAKE_PDF_CONTENT, "application/pdf")}
    
    # First upload (it may already exist, that is fine)
    client.post("/api/v1/documents", files=files)
    
    # Second identical upload
    response = client.post("/api/v1/documents", files=files)
    
    assert response.status_code == 200
    data = response.json()
    # It must return "skipped" to comply with the Incremental Ingestion requirement
    assert data["status"] == "skipped"
    assert "already exists" in data["message"]

def test_chat_intent_router_greeting():
    """4. Test that the router intercepts greetings (Tool Integration)."""
    payload = {
        "session_id": "test-session-123",
        "message": "Hello, good morning!"
    }
    response = client.post("/api/v1/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["tool_used"] == "intent_classifier_greeting"
    assert len(data["citations"]) == 0

def test_chat_rag_structure():
    """5. Test that RAG queries return the correct JSON structure."""
    payload = {
        "session_id": "test-session-123",
        "message": "What is the capital of Colombia?"  # General question to observe system behavior
    }
    response = client.post("/api/v1/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate the data contract (Schema)
    assert "answer" in data
    assert "citations" in data
    assert "is_refusal" in data
    assert isinstance(data["citations"], list)
