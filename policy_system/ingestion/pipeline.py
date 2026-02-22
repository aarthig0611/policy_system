"""
Ingestion pipeline: parse → chunk → embed → store.

This module wires DocumentParser → DocumentChunker → LLMProvider (embed) → RAGProvider (store).
It is fully wired in Phase 4; in Phase 3 it operates with stub RAG/LLM providers.
"""

from __future__ import annotations

from pathlib import Path

from policy_system.core.interfaces import LLMProvider, RAGProvider
from policy_system.core.models import Chunk
from policy_system.ingestion.chunker import DocumentChunker
from policy_system.ingestion.parsers.base import DocumentParser, ParsedDocument
from policy_system.ingestion.parsers.docx_parser import DOCXParser
from policy_system.ingestion.parsers.pdf_parser import PDFParser
from policy_system.ingestion.parsers.text_parser import TextParser

_PARSERS: list[DocumentParser] = [PDFParser(), DOCXParser(), TextParser()]


def get_parser(file_path: str | Path) -> DocumentParser:
    """Return the appropriate parser for the given file path."""
    for parser in _PARSERS:
        if parser.supports(file_path):
            return parser
    raise ValueError(f"No parser available for file: {file_path}")


def parse_document(file_path: str | Path, title: str | None = None) -> ParsedDocument:
    """Parse a document file and return a ParsedDocument."""
    parser = get_parser(file_path)
    return parser.parse(file_path, title=title)


def chunk_document(
    parsed_doc: ParsedDocument,
    doc_id: str,
    allowed_roles: list[str],
    is_archived: bool = False,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split a parsed document into Chunk objects."""
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_document(parsed_doc, doc_id, allowed_roles, is_archived)


def ingest_document(
    file_path: str | Path,
    doc_id: str,
    allowed_roles: list[str],
    rag_provider: RAGProvider,
    llm_provider: LLMProvider,
    title: str | None = None,
    is_archived: bool = False,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    replace_existing: bool = True,
) -> dict:
    """
    Full ingestion pipeline: parse → chunk → embed → store.

    Args:
        file_path: Path to the document file.
        doc_id: UUID string of the document (from the SQL documents table).
        allowed_roles: List of role UUID strings that may access this document.
        rag_provider: Implementation of RAGProvider (e.g. ChromaDB).
        llm_provider: Implementation of LLMProvider (e.g. Ollama).
        title: Display title for citations.
        is_archived: Whether the document is archived.
        chunk_size: Override default chunk size.
        chunk_overlap: Override default chunk overlap.
        replace_existing: If True, deletes existing chunks for doc_id before inserting.

    Returns:
        dict with keys: doc_id, chunk_count, page_count
    """
    # 1. Parse
    parsed = parse_document(file_path, title=title)

    # 2. Chunk
    chunks = chunk_document(parsed, doc_id, allowed_roles, is_archived, chunk_size, chunk_overlap)

    if not chunks:
        return {"doc_id": doc_id, "chunk_count": 0, "page_count": parsed.page_count}

    # 3. Idempotent re-ingestion — delete existing chunks for this doc
    if replace_existing:
        rag_provider.delete_by_doc_id(doc_id)

    # 4. Embed in batch and attach to chunks
    texts = [c.text for c in chunks]
    embeddings = llm_provider.embed_batch(texts)
    for chunk, embedding in zip(chunks, embeddings):
        chunk.metadata["embedding"] = embedding

    # 5. Store
    rag_provider.add_chunks(chunks)

    return {
        "doc_id": doc_id,
        "chunk_count": len(chunks),
        "page_count": parsed.page_count,
        "title": parsed.title,
    }
