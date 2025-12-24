from uuid import UUID
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List

from models.schemas import UploadResponse, DocumentMetadata
from models.responses import ErrorResponse
from services.session_manager import session_manager
from services.document_manager import document_manager
from core.logging import (
    log_upload_start, log_upload_complete, log_upload_rejected,
    log_error, LogCategory
)

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post(
    "/",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def upload_files(
    user_id: UUID = Form(...),
    session_id: UUID = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Upload documents for a session.
    
    Rules:
    - Max 5 files per session
    - Allowed types: PDF, DOCX, TXT, MD
    - Max size: 10MB per file
    - Session must exist and be owned by user
    - Duplicate names allowed (will hash later)
    """
    user_id_str = str(user_id)
    session_id_str = str(session_id)
    
    # Validate UUIDs
    if not session_manager.validate_uuid(user_id_str):
        log_upload_rejected(user_id_str, session_id_str, "Invalid user_id format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format"
        )
    
    if not session_manager.validate_uuid(session_id_str):
        log_upload_rejected(user_id_str, session_id_str, "Invalid session_id format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format"
        )
    
    # Check if files provided
    if not files:
        log_upload_rejected(user_id_str, session_id_str, "No files provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    # Log upload start
    log_upload_start(user_id_str, session_id_str, len(files))
    
    # Process uploads
    try:
        successful_docs, errors = await document_manager.process_upload(
            user_id_str, session_id_str, files
        )
        
        # Log results
        for doc in successful_docs:
            log_upload_complete(user_id_str, session_id_str, 
                              str(doc.document_id), doc.document_name)
        
        for error in errors:
            log_upload_rejected(user_id_str, session_id_str, error)
        
        # Return response
        if successful_docs:
            return UploadResponse(
                success=True,
                message=f"Successfully uploaded {len(successful_docs)} file(s)",
                documents=successful_docs,
                errors=errors if errors else []
            )
        else:
            # All files failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All uploads failed: {'; '.join(errors)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        log_error("Unexpected error during upload", e, 
                 user_id=user_id_str, session_id=session_id_str)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )