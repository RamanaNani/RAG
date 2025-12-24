import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import shutil

from core.constants import SESSION_EXPIRY_HOURS, TEMP_STORAGE_BASE
from core.logging import log_session_created, log_session_expired, log_security_violation

class SessionManager:
    '''
    Manages user sessions in-memory.

    Responsible for:
    - Validate UUID format
    - Track active sessions state
    - Reject malformed requests
    - Handle session expiration
    - Clean up temporary storage
    '''

    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._user_sessions: Dict[str, str] = {}  # user_id -> session_id (single active session)

    def validate_uuid(self, uuid_str: str) -> bool:
        '''
        Validate if the provided string is a valid UUID.
        '''
        try:
            uuid.UUID(uuid_str)
            return True
        except ValueError:
            return False

    def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        '''
        Create a new session for a user.

        If user has existing sessions, It's expired first.
        Returns the new session ID.
        '''
        if not self.validate_uuid(user_id):
            raise ValueError(f"Invalid user ID: {user_id}")

        # Expire existing session if any
        if user_id in self._user_sessions:
            old_session_id = self._user_sessions[user_id]
            self.expire_session(old_session_id)
        
        # Generate new session ID if not provided
        if session_id:
            if not self.validate_uuid(session_id):
                raise ValueError(f"Invalid session ID: {session_id}")
            new_session_id = session_id
        else:
            new_session_id = str(uuid.uuid4())
        
        #check if session ID is already in use
        if new_session_id in self._sessions:
            log_security_violation(user_id, new_session_id, "Session ID already in use")
            raise ValueError(f"Session ID already in use: {new_session_id}")
        
        # Create session
        now = datetime.utcnow()
        self._sessions[new_session_id] = {
            "user_id": user_id,
            "created_at": now,
            "expires_at": now + timedelta(hours=SESSION_EXPIRY_HOURS),
            "document_count": 0
        }
        self._user_sessions[user_id] = new_session_id

        log_session_created(user_id, new_session_id)
        return new_session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        ''' Get session info if valid and not expired, None otherwise.'''
        if not self.validate_uuid(session_id):
            return None
        
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        # Check expiry
        if datetime.utcnow() > session["expires_at"]:
            self.expire_session(session_id)
            return None
        
        return session
    
    def session_exists(self, session_id: str) -> bool:
        ''' Check if a session exists and is valid.'''
        return self.get_session(session_id) is not None

    def validate_session_access(self, user_id: str, session_id: str) -> bool:
        """
        Validate if a session is valid and belongs to the user.
        Returns True if valid, False otherwise.
        Note: Parameter order is (user_id, session_id) to match usage in code.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        if session["user_id"] != user_id:
            log_security_violation(user_id, session_id, "Session access denied")
            return False
        
        return True
    
    def increment_document_count(self, session_id: str):
        ''' Increment the document count for a session.'''
        session = self.get_session(session_id)
        if session:
            session["document_count"] += 1

    def get_document_count(self, session_id: str) -> int:
        ''' Get the document count for a session.'''
        session = self.get_session(session_id)
        return session["document_count"] if session else 0

    def expire_session(self, session_id: str):
        ''' Expire a session.'''
        if session_id not in self._sessions:
            return 
        
        session = self._sessions[session_id]
        user_id = session["user_id"]

        # Remove from tracking
        if user_id in self._user_sessions:
            if self._user_sessions[user_id] == session_id:
                del self._user_sessions[user_id]
        
        del self._sessions[session_id]

        self._cleanup_session_directory(session_id)

        log_session_expired(session_id)

    def _cleanup_session_directory(self, session_id: str):
        ''' Clean up the session directory.'''
        session_dir = TEMP_STORAGE_BASE / session_id
        if session_dir.exists() and session_dir.is_dir():
            try:
                shutil.rmtree(session_dir)
            except Exception as e:
                from core.logging import log_error
                log_error(f"Error cleaning up session directory: {e}", session_id=session_id)

    def cleanup_expired_sessions(self):
        ''' Cleanup expired sessions.'''
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self._sessions.items()
            if now > session["expires_at"]
        ]

        for session_id in expired:
            self.expire_session(session_id)
    
    def get_all_sessions(self) -> Dict[str, Dict]:
        ''' Get all sessions.'''
        return self._sessions.copy()

session_manager = SessionManager()