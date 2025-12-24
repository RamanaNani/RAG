from pathlib import Path
from enum import Enum
import dotenv

#File upload constants
MAX_FILES_PER_SESSION = 5
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

#File extension and mime type constants
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}

#Session constants
SESSION_EXPIRY_HOURS = 24
TEMP_STORAGE_BASE = Path("/tmp")

#logging categories
class LogCategory(str, Enum):
    SESSION = "SESSION"
    UPLOAD = "UPLOAD"
    SECURITY = "SECURITY"
    ERROR = "ERROR"
    SYSTEM = "SYSTEM"