from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    user_id: UUID
    session_id: UUID
    system_prompt: str = Field(..., min_length=1)
    user_message: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "system_prompt": "You are a helpful assistant.",
                "user_message": "What is in my documents?"
            }
        }

class UploadRequest(BaseModel):
    """Request schema for upload endpoint (metadata only, files come via multipart)."""
    user_id: UUID
    session_id: UUID

class DocumentMetadata(BaseModel):
    """Metadata for an uploaded document."""
    session_id: UUID
    document_id: UUID
    document_name: str
    document_hash: str  # SHA256 hash
    uploaded_at: datetime
    file_size: int  # in bytes
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "document_id": "123e4567-e89b-12d3-a456-426614174002",
                "document_name": "policy.pdf",
                "document_hash": "a1b2c3d4e5f6...",
                "uploaded_at": "2024-01-15T10:30:00Z",
                "file_size": 1048576
            }
        }

class UploadResponse(BaseModel):
    """Response schema for upload endpoint."""
    success: bool
    message: str
    documents: List[DocumentMetadata] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class TextBlock(BaseModel):
    """A block of text from a document."""
    text: str
    page: int
    section: Optional[str] = None

class ImageAsset(BaseModel):
    """An image asset from a document."""
    image_url: str # UUID
    session_id: UUID
    document_id: UUID
    page: int
    image_path: str
    format: str

class DocumentContent(BaseModel):
    """The content of a document."""
    text_blocks: List[TextBlock]
    images: List[ImageAsset]

class ChunkMetadata(BaseModel):
    """Metadata for a chunk of content."""
    chunk_id: str
    session_id: UUID
    document_id: UUID
    page: int
    chunk_index: int
    text: str
    image_refs: List[str] = Field(default_factory=list)
    embedding_model: str = "bge-m3"