import uuid
from pathlib import Path

from models.schemas import DocumentContent
from Ingestion.text_extractor import PDFTextExtractor
from Ingestion.image_extractor import ImageExtractor
from Ingestion.chunker import Chunker

DATA_DIR = Path(__file__).parent / "data"


def test_pdf_text_and_images_then_chunk():
    session_id = uuid.uuid4()
    document_id = uuid.uuid4()

    pdf_path = DATA_DIR / "sample.pdf"
    assert pdf_path.exists()

    text_blocks = PDFTextExtractor.extract(pdf_path)
    images = ImageExtractor.extract_images(pdf_path, session_id=session_id, document_id=document_id)

    doc = DocumentContent(text_blocks=text_blocks, images=images)

    chunks = Chunker.chunk(
        doc,
        session_id=session_id,
        document_id=document_id,
        strategy="recursive",
        chunk_size=400,
        chunk_overlap=50,
        embedding_model="BAAI/bge-m3",
    )

    assert len(chunks) > 0

    # image_refs should be list of dicts with your 5 keys
    for c in chunks:
        for img in c.image_refs:
            assert set(img.keys()) == {"image_id", "session_id", "document_id", "page", "image_path"}
            assert img["page"] == c.page
