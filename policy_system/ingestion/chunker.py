"""
Text chunker — wraps RecursiveCharacterTextSplitter and produces Chunk dataclasses.

Each Chunk carries:
  - chunk_id: stable, deterministic ID for idempotent re-ingestion
  - page_number + para_number: required for Detailed Response citations
  - allowed_roles: role UUIDs passed through from document metadata
  - is_archived: propagated from document metadata
"""

from __future__ import annotations

import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

from policy_system.config import settings
from policy_system.core.models import Chunk
from policy_system.ingestion.parsers.base import ParsedDocument


def _make_chunk_id(doc_id: str, page: int | None, para: int | None, index: int) -> str:
    """Generate a stable, deterministic chunk ID."""
    raw = f"{doc_id}_{page}_{para}_{index}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]  # noqa: S324 - not for crypto


class DocumentChunker:
    """
    Splits parsed document pages into Chunk dataclasses.

    Uses RecursiveCharacterTextSplitter from langchain-text-splitters.
    No other LangChain dependencies are pulled in.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or settings.chunk_size,
            chunk_overlap=chunk_overlap or settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_document(
        self,
        doc: ParsedDocument,
        doc_id: str,
        allowed_roles: list[str],
        is_archived: bool = False,
    ) -> list[Chunk]:
        """
        Chunk a parsed document into Chunk dataclasses.

        Each chunk is tied to the page and approximate paragraph it came from.
        chunk_id is deterministic for idempotent re-ingestion.
        """
        chunks: list[Chunk] = []
        global_index = 0

        for page in doc.pages:
            if not page.text.strip():
                continue

            # Split the page text into sub-chunks
            sub_chunks = self._splitter.split_text(page.text)

            for para_idx, text in enumerate(sub_chunks):
                if not text.strip():
                    continue

                chunk_id = _make_chunk_id(doc_id, page.page_number, para_idx, global_index)
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        doc_title=doc.title,
                        text=text.strip(),
                        allowed_roles=list(allowed_roles),
                        is_archived=is_archived,
                        page_number=page.page_number,
                        para_number=para_idx,
                        metadata={
                            "source": doc.source_path,
                            "total_pages": doc.page_count,
                        },
                    )
                )
                global_index += 1

        return chunks
