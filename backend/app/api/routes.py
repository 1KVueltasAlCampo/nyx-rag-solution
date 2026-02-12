from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.deduplication import deduplication_service
from app.services.ingestion import ingestion_service
from app.models.schemas import IngestionResponse, DocumentMetadata
from datetime import datetime
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat import chat_service

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
    Orchestrates the document ingestion pipeline.

    Calculates the file hash to check for duplicates before processing.
    If the file is new, it proceeds with parsing, chunking, embedding, and indexing.

    Args:
        file (UploadFile): The binary file (PDF or Text) to be ingested.

    Returns:
        IngestionResponse: JSON object containing the processing status ('processed' or 'skipped')
        and metadata about the document.

    Raises:
        HTTPException: If the ingestion process fails or encounters a server error.
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
        result = ingestion_service.process_document(file, file_hash)

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
    
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question to the RAG system",
    description="Multi-turn conversation with citation support."
)
async def chat(request: ChatRequest):
    """
    Processes a user query through the RAG pipeline.

    This endpoint manages the conversation flow, including:
    - Intent classification (Tool Integration).
    - Semantic retrieval of relevant context.
    - Prompt construction with history.
    - Generation of a grounded answer with citations.

    Args:
        request (ChatRequest): The request body containing 'session_id' and 'message'.

    Returns:
        ChatResponse: The AI's answer, list of citations, and refusal status.
    """
    return await chat_service.process_query(request.session_id, request.message)

@router.get(
    "/chunks/{doc_id}/{chunk_index}",
    summary="Get chunk content",
    description="Returns the raw text of a specific chunk for evidence verification."
)
async def get_chunk(doc_id: str, chunk_index: int):
    """
    Retrieves the raw text of a specific document chunk.

    Used by the frontend's Evidence Inspector to verify the source of information
    displayed in citations. It acts as a transparent verification mechanism.

    Args:
        doc_id (str): The unique hash identifier of the document.
        chunk_index (int): The specific index of the chunk within the document.

    Returns:
        dict: A dictionary containing the 'doc_id', 'chunk_index', and the raw 'content'.
    """
    content = chat_service.get_chunk_text(doc_id, chunk_index)
    return {"doc_id": doc_id, "chunk_index": chunk_index, "content": content}