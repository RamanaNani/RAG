from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from models.schemas import ChatRequest
from models.responses import ErrorResponse
from services.session_manager import session_manager
from core.logging import log_security_violation, log_error

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
async def chat(request: ChatRequest):
    """
    Chat endpoint (stub - RAG not implemented yet).
    
    Validates session and user access.
    """
    user_id_str = str(request.user_id)
    session_id_str = str(request.session_id)
    
    # Validate session exists
    if not session_manager.session_exists(session_id_str):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session does not exist or has expired"
        )
    
    # Validate session ownership
    if not session_manager.validate_session_access(user_id_str, session_id_str):
        log_security_violation(user_id_str, session_id_str, 
                             "Unauthorized chat access attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this session"
        )
    
    # TODO: Implement RAG logic here
    return {
        "message": "Chat endpoint - RAG implementation pending",
        "user_message": request.user_message,
        "system_prompt": request.system_prompt
    }