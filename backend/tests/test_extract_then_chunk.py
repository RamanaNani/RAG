import uuid
from pathlib import Path

from models.schemas import DocumentContent
from Ingestion.text_extractor import TXTTextExtractor, MDTextExtractor
from Ingestion.chunker import Chunker

DATA_DIR = Path(__file__).parent / "data"


def test_txt_extract_then_chunk():
    session_id = uuid.uuid4()
    document_id = uuid.uuid4()

    file_path = DATA_DIR / "sample.txt"
    assert file_path.exists()

    blocks = TXTTextExtractor.extract(file_path)
    doc = DocumentContent(text_blocks=blocks, images=[])

    chunks = Chunker.chunk(
        doc,
        session_id=session_id,
        document_id=document_id,
        strategy="recursive",
        chunk_size=300,
        chunk_overlap=50,
        embedding_model="BAAI/bge-m3",
    )

    assert len(chunks) > 0
    assert all(c.page >= 1 for c in chunks)
    assert all(isinstance(c.image_refs, list) for c in chunks)


def test_md_extract_then_chunk():
    session_id = uuid.uuid4()
    document_id = uuid.uuid4()

    file_path = DATA_DIR / "sample.md"
    assert file_path.exists()

    blocks = MDTextExtractor.extract(file_path)
    doc = DocumentContent(text_blocks=blocks, images=[])

    chunks = Chunker.chunk(
        doc,
        session_id=session_id,
        document_id=document_id,
        strategy="recursive",
        chunk_size=300,
        chunk_overlap=50,
        embedding_model="BAAI/bge-m3",
    )

    assert len(chunks) > 0
    assert min({c.page for c in chunks}) >= 1
