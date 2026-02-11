from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.deduplication import deduplication_service
from app.services.ingestion import ingestion_service
from app.models.schemas import IngestionResponse, DocumentMetadata
from datetime import datetime

router = APIRouter()

@router.post(
    "/documents",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest a PDF or Text file",
    description="Uploads a document. If the document content (hash) already exists, it skips processing."
)
async def ingest_document(file: UploadFile = File(...)):
    """
    Orchestrates the ingestion flow: Hash Check -> Ingestion -> Registration.
    """
    try:
        # 1. Read file content to calculate hash
        # Warning: For massive files (>1GB), this should be streamed. For this challenge, I'm going to assume memory is fine.
        content = await file.read()
        file_hash = deduplication_service.calculate_hash(content)

        # 2. Check for Duplicates (The Gatekeeper)
        if deduplication_service.is_duplicate(file_hash):
            return IngestionResponse(
                message=f"Document '{file.filename}' already exists. Skipping ingestion.",
                status="skipped",
                data=DocumentMetadata(
                    filename=file.filename,
                    content_hash=file_hash,
                    upload_date=datetime.now(),
                    doc_id=file_hash,
                    chunk_count=0 
                )
            )

        # 3. Reset file cursor
        await file.seek(0)

        # 4. Process the Document (The Heavy Lifting)
        # Note: In a real production app, this should be a BackgroundTask to avoid blocking.
        result = await ingestion_service.process_document(file, file_hash)

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        # 5. Register the successful ingestion
        deduplication_service.register_file(file_hash, file.filename)

        return IngestionResponse(
            message="Document processed and indexed successfully.",
            status="processed",
            data=DocumentMetadata(
                filename=file.filename,
                content_hash=file_hash,
                upload_date=datetime.now(),
                doc_id=file_hash,
                chunk_count=result.get("chunks_created", 0)
            )
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")