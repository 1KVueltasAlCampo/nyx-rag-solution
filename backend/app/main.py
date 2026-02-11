from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="NYX RAG Solution",
    description="API para el reto técnico de Double V Partners",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción esto se restringe, se usa solo para el reto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
async def health_check():
    """
    Endpoint de verificación de estado.
    Retorna el estado del servicio y configuración básica.
    """
    return {
        "status": "healthy",
        "service": "nyx-rag-backend",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "components": {
            "database": "disconnected", # Nota: Conectar Quadrant despues
            "llm": "gemini-1.5-flash"
        }
    }

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Bienvenido al API de NYX RAG. Ve a /docs para la documentación Swagger."}