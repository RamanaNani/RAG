"""
Generate embeddings for text chunks using BGE-M3 or alternative models.
"""
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from core.logging import log_error, LogCategory

class Embedder:
    """Generate embeddings for text using BGE-M3 model."""
    
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """
        Initialize embedder with model.
        
        Args:
            model_name: HuggingFace model name (default: BAAI/bge-m3)
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model."""
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            log_error(f"Error loading embedding model {self.model_name}", e)
            # Fallback to a smaller model if bge-m3 fails
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.model_name = "all-MiniLM-L6-v2"
            except Exception as e2:
                log_error("Error loading fallback embedding model", e2)
                raise
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each as List[float])
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        if not texts:
            return []
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            
            # Convert to list of lists
            return embeddings.tolist()
        
        except Exception as e:
            log_error(f"Error generating embeddings for {len(texts)} texts", e)
            raise
    
    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector as List[float]
        """
        return self.embed([text])[0]