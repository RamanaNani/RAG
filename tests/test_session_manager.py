# tests/test_session_manager.py
import pytest
import uuid
from datetime import datetime, timedelta

from services.session_manager import SessionManager
from core.constants import SESSION_EXPIRY_HOURS

@pytest.fixture
def session_manager():
    """Create a fresh SessionManager instance for each test"""
    return SessionManager()

def test_validate_uuid_valid(session_manager):
    """Test UUID validation with valid UUID"""
    valid_uuid = str(uuid.uuid4())
    assert session_manager.validate_uuid(valid_uuid) == True

def test_validate_uuid_invalid(session_manager):
    """Test UUID validation with invalid UUID"""
    assert session_manager.validate_uuid("not-a-uuid") == False
    assert session_manager.validate_uuid("123") == False
    assert session_manager.validate_uuid("") == False

def test_create_session(session_manager):
    """Test session creation"""
    user_id = str(uuid.uuid4())
    session_id = session_manager.create_session(user_id)
    
    assert session_id is not None
    # get_session returns dict if session exists and valid, None otherwise
    assert session_manager.get_session(session_id) is not None
    # Verify user_id through validate_session_access
    assert session_manager.validate_session_access(user_id, session_id) == True

def test_create_session_with_custom_id(session_manager):
    """Test creating session with custom session_id"""
    user_id = str(uuid.uuid4())
    custom_session_id = str(uuid.uuid4())
    
    created_id = session_manager.create_session(user_id, custom_session_id)
    assert created_id == custom_session_id
    assert session_manager.get_session(custom_session_id) is not None

def test_session_expiry(session_manager):
    """Test session expiry logic"""
    user_id = str(uuid.uuid4())
    session_id = session_manager.create_session(user_id)
    
    # Manually expire by setting expires_at to past
    session = session_manager._sessions[session_id]
    session["expires_at"] = datetime.utcnow() - timedelta(hours=1)
    
    # Session should not exist anymore (get_session checks expiry and returns None)
    assert session_manager.get_session(session_id) is None

def test_validate_session_access_valid(session_manager):
    """Test valid session access"""
    user_id = str(uuid.uuid4())
    session_id = session_manager.create_session(user_id)
    
    # Method signature is (user_id, session_id)
    assert session_manager.validate_session_access(user_id, session_id) == True

def test_validate_session_access_invalid_user(session_manager):
    """Test session access with wrong user"""
    user_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())
    session_id = session_manager.create_session(user_id)
    
    # Method signature is (user_id, session_id)
    assert session_manager.validate_session_access(other_user_id, session_id) == False

def test_document_count_tracking(session_manager):
    """Test document count increment"""
    user_id = str(uuid.uuid4())
    session_id = session_manager.create_session(user_id)
    
    assert session_manager.get_document_count(session_id) == 0
    
    session_manager.increment_document_count(session_id)
    assert session_manager.get_document_count(session_id) == 1
    
    session_manager.increment_document_count(session_id)
    assert session_manager.get_document_count(session_id) == 2

def test_cleanup_expired_sessions(session_manager):
    """Test cleanup of expired sessions"""
    user_id1 = str(uuid.uuid4())
    user_id2 = str(uuid.uuid4())
    
    session1 = session_manager.create_session(user_id1)
    session2 = session_manager.create_session(user_id2)
    
    # Expire session1
    session_manager._sessions[session1]["expires_at"] = datetime.utcnow() - timedelta(hours=1)
    
    # Cleanup
    session_manager.cleanup_expired_sessions()
    
    assert session_manager.get_session(session1) is None
    assert session_manager.get_session(session2) is not None