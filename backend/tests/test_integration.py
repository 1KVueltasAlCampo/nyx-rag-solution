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
    """
    REQ-1: System Availability & Observability.
    Verifies that the API is reachable and can report the status of its
    internal components (LLM, Vector DB).
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    # Ensures the LLM component is registered in the health report
    assert "llm" in data["components"]

def test_upload_document_happy_path():
    """
    REQ-2: Document Ingestion.
    Verifies that a valid PDF file can be uploaded, hashed, and queued for processing.
    Expects either 'processed' (new) or 'skipped' (if run repeatedly) status.
    """
    files = {"file": (FAKE_FILENAME, FAKE_PDF_CONTENT, "application/pdf")}
    response = client.post("/api/v1/documents", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["processed", "skipped"]
    assert "doc_id" in data["data"]

def test_upload_incremental_ingestion():
    """
    REQ-3: Incremental Ingestion (Deduplication).
    Verifies that uploading the exact same file content twice does NOT trigger
    re-processing. This is critical for efficiency and cost saving.
    """
    files = {"file": (FAKE_FILENAME, FAKE_PDF_CONTENT, "application/pdf")}
    
    # 1. First upload (ensure it exists)
    client.post("/api/v1/documents", files=files)
    
    # 2. Second upload (should be blocked by deduplication service)
    response = client.post("/api/v1/documents", files=files)
    
    assert response.status_code == 200
    data = response.json()
    
    # Assertion: Status MUST be 'skipped' to prove hashing logic works
    assert data["status"] == "skipped"
    assert "already exists" in data["message"]

def test_chat_intent_router_greeting():
    """
    REQ-4: Tool Integration (Intent Classifier).
    Verifies that the semantic router correctly identifies a 'GREETING' intent
    and bypasses the expensive RAG pipeline, returning a fast canned response.
    """
    payload = {
        "session_id": "test-session-123",
        "message": "Hello, good morning!"
    }
    response = client.post("/api/v1/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Assertion: Tool usage must be logged in the response metadata
    assert data["tool_used"] == "intent_classifier_greeting"
    # Assertion: No citations should be generated for a greeting
    assert len(data["citations"]) == 0

def test_chat_rag_structure():
    """
    REQ-5: RAG Response Contract.
    Verifies that a general query returns the strictly defined JSON structure
    required by the frontend (Answer, Citations, Refusal Flag).
    """
    payload = {
        "session_id": "test-session-123",
        "message": "What is the capital of Colombia?"
    }
    response = client.post("/api/v1/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate Pydantic Schema integrity
    assert "answer" in data
    assert "citations" in data
    assert "is_refusal" in data
    assert isinstance(data["citations"], list)