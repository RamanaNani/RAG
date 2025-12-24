import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import UploadFile

from core.constants import MAX_FILES_PER_SESSION, MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS, TEMP_STORAGE_BASE, ALLOWED_MIME_TYPES
from core.logging import log_error
from models.schemas import DocumentMetadata
from services.session_manager import session_manager

class DocumentManager:
    '''
    Manages document uploads and metadata.

    Responsible for:
    - Validate document upload requests
    - Store documents in temporary storage
    - Generate document metadata
    - Validate document content
    '''

    def __init__(self):
        # document_id -> DocumentMetadata
        self._documents: Dict[str, DocumentMetadata] = {}
        # session_id -> List[document_id]
        self._session_documents: Dict[str, List[str]] = {}

    def validate_file(self, file: UploadFile) -> tuple[bool, str]:
        """
        Validate the file upload request.
        Returns is valid and error message.
        """

        filename = file.filename or ""
        file_ext = Path(filename).suffix.lower()

        if file_ext not in ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type: {file_ext}"
        
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            pass
        return True, None

    def check_session_file_limit(self, session_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if the session has reached the file limit.
        Returns (can_upload, error_message).
        """
        current_count = session_manager.get_document_count(session_id)
        if current_count >= MAX_FILES_PER_SESSION:
            return False, f"Session file limit reached: {MAX_FILES_PER_SESSION}"
        return True, None
    
    async def process_upload(
        self,
        user_id: str,
        session_id: str,
        files: List[UploadFile]
    ) -> tuple[List[DocumentMetadata], List[str]]:
        """
        Process the document upload.
        Returns is successful and error message.
        """
        successful = []
        errors = []

        # Validate session
        if not session_manager.session_exists(session_id):
            errors.append("Session does not exist or has expired")
            return successful, errors

        # Validate session ownership
        if not session_manager.validate_session_access(user_id, session_id):
            errors.append("Unauthorized access to session")
            return successful, errors
        
        # Check file limits
        current_count = session_manager.get_document_count(session_id)
        if current_count + len(files) > MAX_FILES_PER_SESSION:
            errors.append(f"Session file limit reached: {MAX_FILES_PER_SESSION}")
            return successful, errors
        
        # Process each file
        for file in files:
            try:
                is_valid, error = self.validate_file(file)
                if not is_valid:
                    errors.append(f"{file.filename}: {error}")
                    continue
                
                # Read file content
                content = await file.read()

                #check file size
                if len(content) > MAX_FILE_SIZE_BYTES:
                    errors.append(f"{file.filename}: File size exceeds limit: {MAX_FILE_SIZE_BYTES} bytes")
                    continue
                
                # Generate document ID and hash
                document_id = str(uuid.uuid4())
                document_hash = hashlib.sha256(content).hexdigest()

                # Create session directory if needed
                session_dir = TEMP_STORAGE_BASE / session_id
                session_dir.mkdir(parents=True, exist_ok=True)

                # Store file
                file_path = session_dir / f"{document_id}{Path(file.filename).suffix}"
                file_path.write_bytes(content)

                # Create metadata
                metadata = DocumentMetadata(
                    session_id=uuid.UUID(session_id),
                    document_id=uuid.UUID(document_id),
                    document_name=file.filename,
                    document_hash=document_hash,
                    uploaded_at=datetime.utcnow(),
                    file_size=len(content)
                )

                #Store metadata and session tracking
                self._documents[document_id] = metadata
                if session_id not in self._session_documents:
                    self._session_documents[session_id] = []
                self._session_documents[session_id].append(document_id)

                # Update session document count
                session_manager.increment_document_count(session_id)

                successful.append(metadata)

            except Exception as e:
                log_error(f"Error processing file {file.filename}: {str(e)}", user_id=user_id, session_id=session_id)
                errors.append(f"{file.filename}: {str(e)}")
            
        return successful, errors

    def get_session_documents(self, session_id: str) -> List[DocumentMetadata]:
        """ Get all documents for a session. """
        document_ids = self._session_documents.get(session_id, [])
        return [self._documents[did] for did in document_ids if did in self._documents]

    def delete_session_documents(self, session_id: str):
        """ Delete all documents for a session. """
        if session_id not in self._session_documents:
            return

        # Remove from session tracking
        for doc_id in self._session_documents[session_id]:
            self._documents.pop(doc_id, None)

        # Remove sesssion entry
        del self._session_documents[session_id]

# Global instance
document_manager = DocumentManager()