from pathlib import Path
from uuid import UUID
from typing import List, Optional

from models.schemas import DocumentContent, TextBlock, ImageAsset
from Ingestion.loader import FileLoader
from Ingestion.text_extractor import PDFTextExtractor, DOCXTextExtractor, TXTTextExtractor, MDTextExtractor
from Ingestion.image_extractor import ImageExtractor
from Ingestion.embedder import Embedder
from Ingestion.chunker import Chunker
from Ingestion.registry import QdrantRegistry
from core.logging import log_error, LogCategory, log_event

class IngestionPipeline:
    """
    Pipeline for ingesting documents into RAG.
    """

    def __init__(self, embedder_model: str = "BAAI/bge-m3", registry_url: str = "http://localhost:6333", qdrant_collection: str = "rag_chunks"):
        """
        Initialize the ingestion pipeline.

        Args:
            embedder_model: The model to use for embedding.
            registry_url: The URL of the registry.
            qdrant_collection: The name of the collection to use in Qdrant.
        """
        self.loader = FileLoader()
        self.embedder = Embedder(model_name=embedder_model)
        self.registry = QdrantRegistry(url=registry_url, collection_name=qdrant_collection)
        self.chunker = Chunker()

    def run_until_chunking(
        self,
        file_path: Path,
        session_id: UUID,
        document_id: UUID
    ) -> Optional[DocumentContent]:
        """
        Run the ingestion pipeline until chunking.
        
        Args:
            file_path: Path to the document file
            session_id: Session UUID
            document_id: Document UUID
            
        Returns:
            DocumentContent with extracted text and images, or None if failed
        """
        try:
            log_event(LogCategory.INGESTION, "INFO", f"Starting ingestion pipeline for {file_path.name}")
            
            # Step 1: Load file
            file_type, content = self.loader.load_file(file_path)
            if not file_type or not content:
                log_error(LogCategory.INGESTION, f"Failed to load file: {file_path}")
                return None
            
            log_event(LogCategory.INGESTION, "INFO", f"Loaded file type: {file_type}")
            
            # Step 2: Extract text based on file type
            text_blocks = []
            if file_type == ".pdf":
                text_blocks = PDFTextExtractor.extract(file_path)
            elif file_type == ".docx":
                text_blocks = DOCXTextExtractor.extract(file_path)
            elif file_type == ".txt":
                text_blocks = TXTTextExtractor.extract(file_path)
            elif file_type == ".md":
                text_blocks = MDTextExtractor.extract(file_path)
            else:
                log_error(LogCategory.INGESTION, f"Unsupported file type: {file_type}")
                return None
            
            if not text_blocks:
                log_error(LogCategory.INGESTION, f"No text extracted from {file_path}")
                return None
            
            log_event(LogCategory.INGESTION, "INFO", f"Extracted {len(text_blocks)} text blocks")
            
            # Step 3: Extract images (only for PDF)
            images = []
            if file_type == ".pdf":
                images = ImageExtractor.extract_images(file_path, session_id, document_id)
                log_event(LogCategory.INGESTION, "INFO", f"Extracted {len(images)} images")
            
            # Step 4: Create DocumentContent
            doc_content = DocumentContent(
                text_blocks=text_blocks,
                images=images
            )
            
            log_event(LogCategory.INGESTION, "INFO", f"Created DocumentContent with {len(text_blocks)} text blocks and {len(images)} images")
            
            return doc_content
            
        except Exception as e:
            log_error(LogCategory.INGESTION, f"Error in ingestion pipeline: {str(e)}", e)
            return None

    def run_full_pipeline(
        self,
        file_path: Path,
        session_id: UUID,
        document_id: UUID,
        chunk_strategy: str = "semantic",
        chunk_size: int = 1400,
        chunk_overlap: int = 150
    ) -> bool:
        """
        Run the complete ingestion pipeline including chunking, embedding, and storage.
        
        Args:
            file_path: Path to the document file
            session_id: Session UUID
            document_id: Document UUID
            chunk_strategy: "semantic" or "recursive"
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks (recursive only)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Run until chunking
            doc_content = self.run_until_chunking(file_path, session_id, document_id)
            if not doc_content:
                return False
            
            # Step 5: Chunk the document
            chunks = self.chunker.chunk(
                doc_content,
                session_id=session_id,
                document_id=document_id,
                strategy=chunk_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            if not chunks:
                log_error(LogCategory.INGESTION, "No chunks generated")
                return False
            
            log_event(LogCategory.INGESTION, "INFO", f"Generated {len(chunks)} chunks")
            
            # Step 6: Generate embeddings
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedder.embed(texts)
            
            log_event(LogCategory.INGESTION, "INFO", f"Generated embeddings for {len(chunks)} chunks")
            
            # Step 7: Store in registry
            success = self.registry.store_chunks(chunks, embeddings)
            if success:
                log_event(LogCategory.INGESTION, "INFO", f"Successfully stored {len(chunks)} chunks in registry")
            else:
                log_error(LogCategory.INGESTION, "Failed to store chunks in registry")
            
            return success
            
        except Exception as e:
            log_error(LogCategory.INGESTION, f"Error in full pipeline: {str(e)}", e)
            return False
