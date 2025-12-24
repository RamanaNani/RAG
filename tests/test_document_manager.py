# tests/test_document_manager.py
import pytest
import uuid
from io import BytesIO
from fastapi import UploadFile

from services.document_manager import DocumentManager
from services.session_manager import session_manager as global_session_manager
from core.constants import MAX_FILES_PER_SESSION, MAX_FILE_SIZE_BYTES

@pytest.fixture
def document_manager():
    return DocumentManager()

@pytest.fixture
def test_session():
    """Create a test session using the global session_manager"""
    # Clean up any existing sessions first
    global_session_manager.cleanup_expired_sessions()
    # Clear all sessions for clean test
    global_session_manager._sessions.clear()
    global_session_manager._user_sessions.clear()
    
    user_id = str(uuid.uuid4())
    session_id = global_session_manager.create_session(user_id)
    yield user_id, session_id
    
    # Cleanup after test
    if session_id in global_session_manager._sessions:
        global_session_manager.expire_session(session_id)

def create_test_file(filename: str, content: bytes = b"test content") -> UploadFile:
    """Helper to create a test UploadFile"""
    file_obj = BytesIO(content)
    return UploadFile(
        filename=filename,
        file=file_obj,
        size=len(content)
    )

def test_validate_file_valid_txt(document_manager):
    """Test validation of valid .txt file"""
    file = create_test_file("test.txt", b"content")
    is_valid, error = document_manager.validate_file(file)
    assert is_valid == True
    assert error is None

def test_validate_file_valid_pdf(document_manager):
    """Test validation of valid .pdf file"""
    file = create_test_file("test.pdf", b"%PDF-1.4 fake pdf content")
    is_valid, error = document_manager.validate_file(file)
    assert is_valid == True

def test_validate_file_invalid_extension(document_manager):
    """Test validation of invalid file extension"""
    file = create_test_file("test.exe", b"executable")
    is_valid, error = document_manager.validate_file(file)
    assert is_valid == False
    assert "not allowed" in error.lower() or "unsupported" in error.lower()

@pytest.mark.asyncio
async def test_check_session_file_limit(document_manager, test_session):
    """Test file limit checking"""
    user_id, session_id = test_session
    
    # Fill up to limit
    for i in range(MAX_FILES_PER_SESSION):
        file = create_test_file(f"test{i}.txt", b"content")
        await document_manager.process_upload(user_id, session_id, [file])
    
    # Next file should be rejected
    can_upload, error = document_manager.check_session_file_limit(session_id)
    assert can_upload == False
    assert error is not None and "limit" in error.lower()

@pytest.mark.asyncio
async def test_process_upload_success(document_manager, test_session):
    """Test successful file upload"""
    user_id, session_id = test_session
    file = create_test_file("test.txt", b"test content")
    
    successful, errors = await document_manager.process_upload(user_id, session_id, [file])
    
    assert len(successful) == 1
    assert len(errors) == 0
    assert successful[0].document_name == "test.txt"
    assert successful[0].file_size == len(b"test content")

@pytest.mark.asyncio
async def test_process_upload_file_too_large(document_manager, test_session):
    """Test upload of file exceeding size limit"""
    user_id, session_id = test_session
    large_content = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    file = create_test_file("large.txt", large_content)
    
    successful, errors = await document_manager.process_upload(user_id, session_id, [file])
    
    assert len(successful) == 0
    assert len(errors) == 1
    assert "size" in errors[0].lower() or "exceed" in errors[0].lower()

@pytest.mark.asyncio
async def test_process_upload_invalid_session(document_manager):
    """Test upload to non-existent session"""
    user_id = str(uuid.uuid4())
    fake_session_id = str(uuid.uuid4())
    file = create_test_file("test.txt", b"content")
    
    successful, errors = await document_manager.process_upload(user_id, fake_session_id, [file])
    
    assert len(successful) == 0
    assert len(errors) == 1
    assert "session" in errors[0].lower() or "exist" in errors[0].lower()