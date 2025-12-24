import logging
import sys
from datetime import datetime
from typing import Optional
from core.constants import LogCategory

# Configure logging - use 'logger' to avoid overwriting the logging module
logger = logging.getLogger("rag_backend")
logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def log_event(
    category: LogCategory,
    level: str,
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
):
    '''
    Structured logging function for the RAG backend

    Args:
        category: The category of the event
        level: The level of the event
        message: The message to log
        user_id: The user ID associated with the event
        session_id: The session ID associated with the event
        **kwargs: Additional context to log
    '''
    context = {
        "category": category.value,
        "timestamp": datetime.now().isoformat(),
    }

    if user_id:
        context["user_id"] = user_id
    if session_id:
        context["session_id"] = session_id
    context.update(kwargs)

    formatted_msg = f"{category.value} | {message}"
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items() if k != "category" and v is not None)
        formatted_msg = f"{formatted_msg} | {context_str}"
    
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(formatted_msg)

def log_upload_start(user_id: str, session_id: str, file_count: int):
    log_event(LogCategory.UPLOAD, "INFO", "Upload started",
    user_id=user_id, session_id=session_id, file_count=file_count)

def log_upload_complete(user_id: str, session_id: str, document_id: str, filename: str):
    log_event(LogCategory.UPLOAD, "INFO", "Upload completed",
              user_id=user_id, session_id=session_id, 
              document_id=document_id, filename=filename)

def log_upload_rejected(user_id: str, session_id: str, reason: str):
    log_event(LogCategory.UPLOAD, "WARNING", f"Upload rejected: {reason}",
              user_id=user_id, session_id=session_id)

def log_session_created(user_id: str, session_id: str):
    log_event(LogCategory.SESSION, "INFO", "Session created",
              user_id=user_id, session_id=session_id)

def log_session_expired(session_id: str):
    log_event(LogCategory.SESSION, "INFO", "Session expired",
              session_id=session_id)

def log_security_violation(user_id: str, session_id: str, reason: str):
    log_event(LogCategory.SECURITY, "WARNING", f"Security violation: {reason}",
              user_id=user_id, session_id=session_id)

def log_error(message: str, error: Exception, user_id: Optional[str] = None, 
              session_id: Optional[str] = None):
    log_event(LogCategory.ERROR, "ERROR", f"{message}: {str(error)}",
              user_id=user_id, session_id=session_id, error_type=type(error).__name__)