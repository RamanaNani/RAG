"""
Extract images from PDF documents using PyMuPDF (fitz).
"""
import uuid
from pathlib import Path
from typing import List
from uuid import UUID
import fitz  # PyMuPDF

from models.schemas import ImageAsset
from core.constants import TEMP_STORAGE_BASE
from core.logging import log_error, LogCategory

class ImageExtractor:
    """Extract images from PDF documents."""
    
    @staticmethod
    def extract_images(
        pdf_path: Path,
        session_id: UUID,
        document_id: UUID
    ) -> List[ImageAsset]:
        """
        Extract images from PDF and save them to session directory.
        Returns list of ImageAsset objects.
        """
        images = []
        
        try:
            # Create images directory in session folder
            session_dir = TEMP_STORAGE_BASE / str(session_id)
            images_dir = session_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # Open PDF
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Get image data
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]  # "png", "jpeg", etc.
                        
                        # Generate image ID
                        image_id = str(uuid.uuid4())
                        
                        # Save image
                        image_filename = f"{image_id}.{image_ext}"
                        image_path = images_dir / image_filename
                        image_path.write_bytes(image_bytes)
                        
                        # Create ImageAsset
                        images.append(ImageAsset(
                            image_id=image_id,
                            session_id=session_id,
                            document_id=document_id,
                            page=page_num + 1,  # 1-indexed
                            image_path=str(image_path),
                            format=image_ext
                        ))
                    
                    except Exception as e:
                        log_error(f"Error extracting image {img_index} from page {page_num + 1}", e,
                                 session_id=str(session_id), document_id=str(document_id))
                        continue
            
            doc.close()
        
        except Exception as e:
            log_error(f"Error extracting images from PDF {pdf_path}", e,
                     session_id=str(session_id), document_id=str(document_id))
            return []
        
        return images