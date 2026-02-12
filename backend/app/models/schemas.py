from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentMetadata(BaseModel):
    filename: str
    content_hash: str
    upload_date: datetime
    doc_id: str
    chunk_count: int

class IngestionResponse(BaseModel):
    message: str
    data: Optional[DocumentMetadata] = None
    status: str  # "processed" | "skipped" | "error"

class HealthCheck(BaseModel):
    status: str
    service: str
    environment: str