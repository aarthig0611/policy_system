"""
Citation formatter for Detailed Response mode.

Produces [Doc Title, Page X, Para Y] citation strings from RetrievedChunk objects.
"""

from __future__ import annotations

from policy_system.api.schemas import CitationResponse
from policy_system.core.models import RetrievedChunk


def build_citations(chunks: list[RetrievedChunk]) -> list[CitationResponse]:
    """
    Build a deduplicated list of citation objects from retrieved chunks.

    Deduplication is by (doc_id, page_number, para_number) to avoid
    showing the same location twice when multiple chunks came from the same paragraph.
    """
    seen: set[tuple] = set()
    citations = []

    for chunk in chunks:
        key = (chunk.doc_id, chunk.page_number, chunk.para_number)
        if key in seen:
            continue
        seen.add(key)

        citations.append(
            CitationResponse(
                doc_id=chunk.doc_id,
                doc_title=chunk.doc_title,
                page_number=chunk.page_number,
                para_number=chunk.para_number,
            )
        )

    return citations


def format_citation_text(chunk: RetrievedChunk) -> str:
    """Format a single chunk's citation as a human-readable string."""
    parts = [chunk.doc_title]
    if chunk.page_number is not None:
        parts.append(f"Page {chunk.page_number}")
    if chunk.para_number is not None:
        parts.append(f"Para {chunk.para_number}")
    return "[" + ", ".join(parts) + "]"
