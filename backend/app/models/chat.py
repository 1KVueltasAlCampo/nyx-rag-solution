from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

# --- Request ---
class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID for the conversation session")
    message: str = Field(..., description="The user's question or query")

# --- Citations & Evidence ---
class Citation(BaseModel):
    source_id: str = Field(..., description="The unique ID (chunk_id/hash) of the source text")
    quote: str = Field(..., description="Exact text snippet used as evidence")
    page: Optional[int] = None
    file_name: str

# --- LLM Structured Output (The Contract) ---
class RAGResponse(BaseModel):
    thinking_process: str = Field(..., description="Step-by-step reasoning analysis.")
    answer: str = Field(...)
    citation_ids: List[str] = Field(...)
    is_refusal: bool = Field(...)

# --- API Final Response ---
class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    tool_used: str = "retrieval_augmented_generation"
    is_refusal: bool
    session_id: str

class UserIntent(str, Enum):
    GREETING = "greeting"
    SECURITY_RISK = "security_risk"
    RAG_QUERY = "rag_query"

class IntentClassification(BaseModel):
    intent: UserIntent
    confidence: float
    reasoning: str