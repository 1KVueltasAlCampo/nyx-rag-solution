from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from app.api.routes import router as api_router

load_dotenv()

app = FastAPI(
    title="NYX RAG Solution",
    description="API for the Double V Partners technical challenge",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production this should be restricted; used only for the challenge
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1", tags=["Ingestion"])

@app.get("/health", tags=["System"])
async def health_check():
    """
    Performs a real-time system diagnostic check.
    
    Verifies connectivity to critical infrastructure components (Vector DB)
    and returns the current operational status of the API. This endpoint is 
    typically consumed by load balancers or monitoring tools (e.g., K8s probes).

    Returns:
        dict: System health status, environment info, and component connectivity states.
    """
    # 1. Check Qdrant Connectivity
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
    
    db_status = "unknown"
    try:
        client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=2.0)
        client.get_collections()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    return {
        "status": "healthy", # API itself is alive
        "service": "nyx-rag-backend",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "components": {
            "vector_db": db_status,
            "llm": "gemini-2.0-flash"
        }
    }

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint for API discovery.
    
    Returns:
        dict: A welcome message and guidance to locate the OpenAPI documentation.
    """
    return {"message": "Welcome to the NYX RAG API. Go to /docs for the Swagger documentation."}