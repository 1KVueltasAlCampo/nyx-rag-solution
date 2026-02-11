from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
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
    Health check endpoint.
    Returns the service status and basic configuration details.
    """
    return {
        "status": "healthy",
        "service": "nyx-rag-backend",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "components": {
            "database": "disconnected",  # Note: Connect Quadrant later
            "llm": "gemini-1.5-flash"
        }
    }

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the NYX RAG API. Go to /docs for the Swagger documentation."}
