"""
Text extraction from various document formats.
Preserves reading order, page numbers, and headings.
"""
import re
from pathlib import Path
from typing import List, Optional
import pdfplumber
from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

from models.schemas import TextBlock
from core.logging import log_error, LogCategory

class BaseTextExtractor:
    """Base class for text extractors."""
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace while preserving structure."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        return text.strip()

class PDFTextExtractor(BaseTextExtractor):
    """Extract text from PDF files using pdfplumber."""
    
    @staticmethod
    def extract(file_path: Path) -> List[TextBlock]:
        """
        Extract text blocks from PDF preserving page numbers and reading order.
        Returns list of TextBlock objects.
        """
        text_blocks = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text preserving layout
                    text = page.extract_text()
                    
                    if text:
                        # Normalize whitespace
                        text = PDFTextExtractor.normalize_whitespace(text)
                        
                        # Try to detect headings (simple heuristic: short lines, bold, or all caps)
                        lines = text.split('\n')
                        current_section = None
                        current_text = []
                        
                        for line in lines:
                            line_stripped = line.strip()
                            if not line_stripped:
                                continue
                            
                            # Simple heading detection: short line, possibly all caps or starts with number
                            is_heading = (
                                len(line_stripped) < 100 and
                                (line_stripped.isupper() or 
                                 re.match(r'^\d+[\.\)]\s+', line_stripped) or
                                 re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$', line_stripped))
                            )
                            
                            if is_heading and not current_text:
                                current_section = line_stripped
                            else:
                                current_text.append(line_stripped)
                        
                        # Create text block for the page
                        if current_text:
                            text_blocks.append(TextBlock(
                                text='\n'.join(current_text),
                                page=page_num,
                                section=current_section
                            ))
                        elif text:
                            # Fallback: use all text if no structure detected
                            text_blocks.append(TextBlock(
                                text=text,
                                page=page_num,
                                section=None
                            ))
        
        except Exception as e:
            log_error(f"Error extracting text from PDF {file_path}", e,
                     session_id=str(file_path.parent.name))
            return []
        
        return text_blocks

class DOCXTextExtractor(BaseTextExtractor):
    """Extract text from DOCX files using python-docx."""
    
    @staticmethod
    def extract(file_path: Path) -> List[TextBlock]:
        """
        Extract text blocks from DOCX preserving structure.
        Note: DOCX doesn't have explicit page numbers, so we use paragraph order.
        """
        text_blocks = []
        
        try:
            doc = Document(file_path)
            current_page = 1  # DOCX doesn't have pages, use paragraph index
            current_section = None
            current_text = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                
                if not text:
                    continue
                
                # Detect headings (styles with "Heading" in name)
                if para.style and "Heading" in para.style.name:
                    # Save previous block if exists
                    if current_text:
                        text_blocks.append(TextBlock(
                            text='\n'.join(current_text),
                            page=current_page,
                            section=current_section
                        ))
                        current_text = []
                    
                    current_section = text
                    current_page += 1
                else:
                    current_text.append(text)
            
            # Add final block
            if current_text:
                text_blocks.append(TextBlock(
                    text='\n'.join(current_text),
                    page=current_page,
                    section=current_section
                ))
        
        except Exception as e:
            log_error(f"Error extracting text from DOCX {file_path}", e,
                     session_id=str(file_path.parent.name))
            return []
        
        return text_blocks

class TXTTextExtractor(BaseTextExtractor):
    """Extract text from plain text files."""
    
    @staticmethod
    def extract(file_path: Path) -> List[TextBlock]:
        """Extract text from TXT file."""
        try:
            text = file_path.read_text(encoding='utf-8')
            text = TXTTextExtractor.normalize_whitespace(text)
            
            # Split into paragraphs and assign page numbers
            paragraphs = text.split('\n\n')
            text_blocks = []
            
            for idx, para in enumerate(paragraphs, start=1):
                if para.strip():
                    text_blocks.append(TextBlock(
                        text=para.strip(),
                        page=idx,  # Use paragraph index as page
                        section=None
                    ))
            
            return text_blocks if text_blocks else [TextBlock(text=text, page=1, section=None)]
        
        except Exception as e:
            log_error(f"Error extracting text from TXT {file_path}", e,
                     session_id=str(file_path.parent.name))
            return []

class MDTextExtractor(BaseTextExtractor):
    """Extract text from Markdown files."""
    
    @staticmethod
    def extract(file_path: Path) -> List[TextBlock]:
        """Extract text from Markdown file, preserving headings as sections."""
        try:
            text = file_path.read_text(encoding='utf-8')
            text = MDTextExtractor.normalize_whitespace(text)
            
            lines = text.split('\n')
            text_blocks = []
            current_section = None
            current_text = []
            page = 1
            
            for line in lines:
                line_stripped = line.strip()
                
                # Detect markdown headings
                if line_stripped.startswith('#'):
                    # Save previous block
                    if current_text:
                        text_blocks.append(TextBlock(
                            text='\n'.join(current_text),
                            page=page,
                            section=current_section
                        ))
                        current_text = []
                        page += 1
                    
                    # Extract heading text (remove # and whitespace)
                    current_section = re.sub(r'^#+\s+', '', line_stripped)
                else:
                    if line_stripped:
                        current_text.append(line_stripped)
            
            # Add final block
            if current_text:
                text_blocks.append(TextBlock(
                    text='\n'.join(current_text),
                    page=page,
                    section=current_section
                ))
            
            return text_blocks if text_blocks else [TextBlock(text=text, page=1, section=None)]
        
        except Exception as e:
            log_error(f"Error extracting text from MD {file_path}", e,
                     session_id=str(file_path.parent.name))
            return []