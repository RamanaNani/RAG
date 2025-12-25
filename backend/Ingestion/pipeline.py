from pathlib import Path
from uuid import UUID
from typing import List, Optional

from models.schemas import DocumentContent, TextBlock, ImageAsset
from Ingestion.loader import FileLoader
from Ingestion.text_extractor import PDFTextExtractor, DOCXTextExtractor, TXTTextExtractor, MDTextExtractor
from Ingestion.image_extractor import ImageExtractor
from Ingestion.embedder import Embedder
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
        