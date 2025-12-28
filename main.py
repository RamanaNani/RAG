from uuid import uuid4

import pytest

from models.schemas import DocumentContent, TextBlock, ImageAsset
from backend.ingestion.chunker import Chunker  # adjust path


def build_doc():
    return DocumentContent(
        text_blocks=[
            TextBlock(page=1, section="A", text="Sentence one. Sentence two. Sentence three."),
            TextBlock(page=1, section="A", text="Qdrant stores vectors. It also stores payloads."),
            TextBlock(page=2, section="B", text="Embedding based chunking is different. It uses cosine similarity."),
        ],
        images=[
            ImageAsset(image_id="img_1", page=1, image_path="/tmp/img_1.png"),
            ImageAsset(image_id="img_2", page=2, image_path="/tmp/img_2.png"),
        ],
    )


def test_preserves_page_boundaries_recursive():
    doc = build_doc()
    session_id = uuid4()
    document_id = uuid4()

    chunks = Chunker.chunk(
        doc,
        session_id=session_id,
        document_id=document_id,
        strategy="recursive",
        chunk_size=60,
        chunk_overlap=10,
    )

    assert len(chunks) > 0
    # ensure every chunk belongs to an existing page
    assert set(c.page for c in chunks).issubset({1, 2})

    # ensure image refs map correctly by page
    for c in chunks:
        if c.page == 1:
            assert c.image_refs == ["img_1"]
        if c.page == 2:
            assert c.image_refs == ["img_2"]


def test_chunk_id_is_stable():
    doc = build_doc()
    session_id = uuid4()
    document_id = uuid4()

    chunks1 = Chunker.chunk(doc, session_id=session_id, document_id=document_id, strategy="recursive", chunk_size=60)
    chunks2 = Chunker.chunk(doc, session_id=session_id, document_id=document_id, strategy="recursive", chunk_size=60)

    assert [c.chunk_id for c in chunks1] == [c.chunk_id for c in chunks2]


@pytest.mark.skipif(
    pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed") is None,
    reason="sentence-transformers not installed",
)
def test_semantic_strategy_runs():
    doc = build_doc()
    session_id = uuid4()
    document_id = uuid4()

    chunks = Chunker.chunk(
        doc,
        session_id=session_id,
        document_id=document_id,
        strategy="semantic",
        chunk_size=120,
        min_chunk_chars=20,
        similarity_threshold=0.55,
        window=1,
    )

    assert len(chunks) > 0
    # still page-bounded and image-linked
    for c in chunks:
        assert c.page in {1, 2}
        if c.page == 1:
            assert c.image_refs == ["img_1"]
        if c.page == 2:
            assert c.image_refs == ["img_2"]
