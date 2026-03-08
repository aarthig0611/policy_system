"""
Citation formatter for Detailed Response mode.

Produces [Doc Title, Page X, Para Y] citation strings from RetrievedChunk objects.
"""

from __future__ import annotations

from backend.api.schemas import CitationResponse
from backend.core.models import RetrievedChunk


def build_citations(chunks: list[RetrievedChunk]) -> list[CitationResponse]:
    """
    Build a numbered list of citation objects from retrieved chunks, preserving
    retrieval order without deduplication.

    Source numbers (1-N) correspond directly to the [N] markers in the LLM response,
    since the context passed to the LLM numbers chunks in the same order.
    """
    return [
        CitationResponse(
            doc_id=chunk.doc_id,
            doc_title=chunk.doc_title,
            page_number=chunk.page_number,
            para_number=chunk.para_number,
        )
        for chunk in chunks
    ]


def format_citation_text(chunk: RetrievedChunk) -> str:
    """Format a single chunk's citation as a human-readable string."""
    parts = [chunk.doc_title]
    if chunk.page_number is not None:
        parts.append(f"Page {chunk.page_number}")
    if chunk.para_number is not None:
        parts.append(f"Para {chunk.para_number}")
    return "[" + ", ".join(parts) + "]"
