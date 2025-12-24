from uuid import UUID
from pydantic import BaseModel
from typing import Optional, Any

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    user_id: Optional[UUID] = None
    session_id: Optional[UUID] = None

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "1.0.0"
    active_sessions: int = 0