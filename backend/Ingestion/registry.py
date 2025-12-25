from typing import List, Dict, Optional, Any
from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from models.schemas import ChunkMetadata
from core.logging import log_error, LogCategory

class QdrantRegistry:
    """
    Manage Vector Storage in Qdrant.
    """

    def __init__(self, url: str = "http://localhost:6333", collection_name: str = "rag_chunks"):
        """
        Initialize the Qdrant registry.

        Args:
            url: The URL of the Qdrant server.
            collection_name: The name of the collection to create.
        """
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self._ensure_collection()

    def _ensure_collection(self):
        """
        Create collection if it doesn't exist.
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                # Get embedding dimesions (BGE-M3 is 1024)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
        
        except Exception as e:
            log_error(f"Error ensuring Qdrant collection exists", e)
            raise

    def store_chunks(self, chunks: List[ChunkMetadata], embeddings: List[List[float]]) -> bool:
        """
        Store chunks and embeddings in Qdrant.
        Args:
            chunks: List of ChunkMetadata objects.
            embeddings: List of embeddings for each chunk.
        Returns:
            True if successful, False otherwise.
        """
        if len(chunks) != len(embeddings):
            log_error(f"Number of chunks and embeddings must match")
            return False
        
        try:
            points = []
            for chunk, embedding in zip(chunks, embeddings):
                point = PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload={
                        "session_id": str(chunk.session_id),
                        "document_id": str(chunk.document_id),
                        "page": chunk.page,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "image_refs": chunk.image_refs,
                        "embedding_model": chunk.embedding_model
                    }
                )
                points.append(point)   
            self.client.upsert(collection_name=self.collection_name, points=points)
            return True
        
        except Exception as e:
            log_error(f"Error storing chunks in Qdrant", e)
            return False

    def retreive_by_session(self, session_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve chunks by session ID.
        Args:
            session_id: The ID of the session.
            limit: The maximum number of chunks to retrieve.
        Returns:
            List of chunk metadata dictionaries.
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=str(session_id))
                        )
                    ]
                ),
                limit=limit
            )

            chunks = []
            for point in results[0]:
                chunks.append({
                    "chunk_id": point.id,
                    "vector": point.vector,
                    "session_id": point.payload.get("session_id"),
                    "document_id": point.payload.get("document_id"),
                    "page": point.payload.get("page"),
                    "chunk_index": point.payload.get("chunk_index"),
                    "text": point.payload.get("text"),
                    "image_refs": point.payload.get("image_refs"),
                    "embedding_model": point.payload.get("embedding_model")
                })
            return chunks
        
        except Exception as e:
            log_error(f"Error retrieving chunks from Qdrant", e)
            return []
        
    def delete_session_chunks(self, session_id: UUID) -> bool:
        """
        Delete chunks by session ID.
        Args:
            session_id: The ID of the session.
        Returns:
            True if successful, False otherwise.
        """
        try:
            chunks = self.retreive_by_session(session_id, limit=10000)
            if not chunks:
                return True
            
            chunk_ids = [chunk["chunk_id"] for chunk in chunks]
            self.client.delete(collection_name=self.collection_name, points_ids=chunk_ids)
            return True
        
        except Exception as e:
            log_error(f"Error deleting chunks from Qdrant", e)
            return False