import os
import shutil
from typing import List
from fastapi import UploadFile

# LangChain & AI Components
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document

# Internal Config
from qdrant_client import QdrantClient
from qdrant_client.http import models

class IngestionService:
    """
    Handles the ingestion pipeline: Loading -> Splitting -> Embedding -> Indexing.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.qdrant_url = os.getenv("QDRANT_HOST", "qdrant")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = "nyx_documents_v2"
        
        self._is_initialized = False

    def _initialize_resources(self):
        """
        Lazily initializes external service connections (Qdrant & Gemini).
        
        This prevents startup crashes if external services are not immediately ready 
        and ensures connections are established only when the first document is processed.
        It implements a singleton-like check to avoid re-initialization.
        """
        if self._is_initialized:
            return

        try:
            # Initialize Embeddings
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                task_type="retrieval_document",
                google_api_key=self.api_key
            )

            # Initialize Qdrant Client
            self.client = QdrantClient(host=self.qdrant_url, port=self.qdrant_port)
            
            # Check Collection
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)

            if not exists:
                print(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=3072, # Gemini default
                        distance=models.Distance.COSINE
                    )
                )
            
            self._is_initialized = True
            print("--- [Lazy Init] Connection Successful ---")
            
        except Exception as e:
            print(f"CRITICAL ERROR connecting to Qdrant: {e}")
            raise e

    def process_document(self, file: UploadFile, file_hash: str) -> dict:
        """
        Executes the full document ingestion pipeline synchronously.
        
        This method handles file saving, content loading, semantic chunking, 
        embedding generation, and vector database indexing. It runs in a thread pool 
        to avoid blocking the main async event loop during I/O operations.

        Args:
            file (UploadFile): The file object uploaded via FastAPI.
            file_hash (str): The pre-calculated MD5 hash of the file content for deduplication.

        Returns:
            dict: A summary object containing status, chunk count, and document ID.
        """
        # A. Lazy Init Check
        self._initialize_resources()

        temp_filename = f"temp_{file.filename}"
        
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # B. Load Document
            documents = self._load_file(temp_filename, file.content_type)
            
            if not documents:
                return {"status": "error", "message": "Could not extract text"}

            # C. Split (Chunking)
            chunks = self._chunk_documents(documents)

            # D. Inject Metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata["file_hash"] = file_hash
                chunk.metadata["filename"] = file.filename
                chunk.metadata["chunk_id"] = i
                page = chunk.metadata.get('page', 0) + 1 
                chunk.metadata["source"] = f"{file.filename} (Page {page})"

            # E. Indexing using langchain-qdrant
            QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                url=f"http://{self.qdrant_url}:{self.qdrant_port}",
                collection_name=self.collection_name,
                force_recreate=False
            )

            return {
                "status": "success", 
                "chunks_created": len(chunks),
                "doc_id": file_hash
            }

        except Exception as e:
            print(f"Ingestion Error: {e}")
            raise e
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    def _load_file(self, path: str, content_type: str) -> List[Document]:
        """
        Selects and executes the appropriate document loader based on file type.

        Currently supports PDF (via PyPDFLoader) and plain text files.

        Args:
            path (str): The local file system path to the temporary file.
            content_type (str): The MIME type of the uploaded file.

        Returns:
            List[Document]: A list of LangChain Document objects containing raw text and basic metadata.
        """
        try:
            if "pdf" in content_type or path.endswith(".pdf"):
                loader = PyPDFLoader(path)
                return loader.load()
            else:
                loader = TextLoader(path)
                return loader.load()
        except Exception as e:
            print(f"Error loading file: {e}")
            return []

    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Splits raw documents into smaller, semantically meaningful text chunks.

        Uses a recursive character splitter to respect sentence boundaries and 
        maintain context overlap, which is critical for retrieval quality.

        Args:
            documents (List[Document]): The raw documents loaded from the file.

        Returns:
            List[Document]: A list of smaller Document objects ready for embedding.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return text_splitter.split_documents(documents)

# Singleton Instance
ingestion_service = IngestionService()