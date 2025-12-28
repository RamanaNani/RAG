"""
Chunking strategy for text blocks.

Implements:
1) REAL semantic chunking (embedding-based boundary detection) using LangChain SemanticChunker
2) Recursive Character Text Splitter using LangChain RecursiveCharacterTextSplitter

Rules:
- Chunk text only
- Preserve page boundaries (never cross pages)
- Attach image_refs from same page (FULL METADATA dicts)
- chunk_id = sha256(session_id|document_id|page|chunk_index)
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional, Any
from uuid import UUID

from models.schemas import DocumentContent, ChunkMetadata

_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    text = (text or "").replace("\u00a0", " ")
    text = _WS.sub(" ", text)
    return text.strip()


def _make_chunk_id(session_id: UUID, document_id: UUID, page: int, chunk_index: int) -> str:
    raw = f"{session_id}|{document_id}|{page}|{chunk_index}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class Chunker:
    """
    Chunks text blocks while preserving page boundaries.
    Supports:
      - semantic (LangChain SemanticChunker)
      - recursive (LangChain RecursiveCharacterTextSplitter)
    """

    @staticmethod
    def chunk(
        document_content: DocumentContent,
        session_id: UUID,
        document_id: UUID,
        *,
        strategy: str = "semantic",   # "semantic" | "recursive"
        embedding_model: str = "BAAI/bge-m3",
        chunk_size: int = 1400,
        chunk_overlap: int = 150,
        # kept for signature compatibility (not strictly used by LangChain splitters)
        min_chunk_chars: int = 300,
        similarity_threshold: float = 0.55,
        window: int = 1,
    ) -> List[ChunkMetadata]:

        # SAFE access
        images = getattr(document_content, "images", None) or []
        text_blocks = getattr(document_content, "text_blocks", None) or []

        # Group images by page with FULL METADATA dicts
        images_by_page: Dict[int, List[Dict[str, Any]]] = {}
        for image in images:
            page = int(getattr(image, "page", 0) or 0)
            if page <= 0:
                continue

            # Support both schema variants: image_id OR image_url
            image_id_val = getattr(image, "image_id", None) or getattr(image, "image_url", "")

            images_by_page.setdefault(page, []).append(
                {
                    "image_id": str(image_id_val),
                    "session_id": str(getattr(image, "session_id", "")),
                    "document_id": str(getattr(image, "document_id", "")),
                    "page": page,
                    "image_path": str(getattr(image, "image_path", "")),
                }
            )

        # Group text blocks by page
        blocks_by_page: Dict[int, List[Any]] = {}
        for tb in text_blocks:
            page = int(getattr(tb, "page", 0) or 0)
            if page <= 0:
                continue
            blocks_by_page.setdefault(page, []).append(tb)

        # Build splitter per strategy (LangChain)
        if strategy == "recursive":
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
            )

            def split_text(text: str) -> List[str]:
                return splitter.split_text(text)

        elif strategy == "semantic":
            # NOTE: SemanticChunker requires embeddings
            from langchain_text_splitters import SemanticChunker
            from langchain_community.embeddings import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model,
                encode_kwargs={"normalize_embeddings": True},
            )

            sem = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=90.0,
            )

            def split_text(text: str) -> List[str]:
                docs = sem.create_documents([text])
                return [_normalize(d.page_content) for d in docs if _normalize(d.page_content)]

        else:
            raise ValueError("strategy must be 'semantic' or 'recursive'")

        chunks: List[ChunkMetadata] = []

        for page in sorted(blocks_by_page.keys()):
            page_blocks = blocks_by_page[page]
            if not page_blocks:
                continue

            # Build page text (still within the page)
            parts: List[str] = []
            last_section: Optional[str] = None

            for b in page_blocks:
                txt = _normalize(getattr(b, "text", "") or "")
                if not txt:
                    continue

                sec = getattr(b, "section", None)
                sec = _normalize(sec) if sec else None
                if sec and sec != last_section:
                    parts.append(f"## {sec}")
                    last_section = sec

                parts.append(txt)

            page_text = "\n\n".join(parts).strip()
            if not page_text:
                continue

            pieces = split_text(page_text)

            image_refs = images_by_page.get(page, [])

            for chunk_index, piece in enumerate(pieces):
                piece = _normalize(piece)
                if not piece:
                    continue

                chunk_id = _make_chunk_id(session_id, document_id, page, chunk_index)

                chunks.append(
                    ChunkMetadata(
                        chunk_id=chunk_id,
                        session_id=session_id,
                        document_id=document_id,
                        page=page,
                        chunk_index=chunk_index,
                        text=piece,
                        image_refs=image_refs,  # LIST OF METADATA DICTS
                        embedding_model=embedding_model,
                    )
                )

        return chunks
