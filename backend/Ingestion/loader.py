from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from core.constants import ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES
from core.logging import log_error, LogCategory

class FileLoader:
    """
    Detects and loads file types into DocumentContent objects.
    """

    @staticmethod
    def detect_file_type(file_path: Path) -> Optional[str]:
        """
        Detect the file type of a file.
        Returns the file extension if valid, None otherwise.
        """
        file_ext = file_path.suffix.lower()
        if file_ext in ALLOWED_EXTENSIONS:
            return file_ext
        return None
    
    @staticmethod
    def get_extractor_class(file_type: str) -> Optional[str]:
        """
        Get the extractor class for a file type.
        Returns the extractor class if valid, None otherwise.
        """
        mapping = {
            ".pdf": "text_extractor.PDFTextExtractor",
            ".docx": "text_extractor.DOCXTextExtractor",
            ".txt": "text_extractor.TXTTextExtractor",
            ".md": "text_extractor.MDTextExtractor",
        }
        return mapping.get(file_type)
    
    @staticmethod
    def load_file(file_path: Path) -> tuple[Optional[str], Optional[bytes]]:
        """
        Load a file and return the file type and content.
        Returns (file_type, file_content).
        """
        try:
            if not file_path.exists():
                log_error(LogCategory.ERROR, f"File not found: {file_path}", Exception(f"File not found: {file_path}"),
                session_id = str(file_path.parent.name))
            return None, None

            file_type = FileLoader.detect_file_type(file_path)
            if not file_type:
                log_error(LogCategory.ERROR, f"Unsupported file type: {file_path.suffix}",
                Exception(f"Unsupported file type: {file_path.suffix}"),
                session_id = str(file_path.parent.name))
                return None, None

            content = file_path.read_bytes()
            return file_type, content
        
        except Exception as e:
            log_error(LogCategory.ERROR, f"Error loading file: {file_path}", e,
            session_id = str(file_path.parent.name))
            return None, None