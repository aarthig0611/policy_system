"""
Core dataclasses shared across all layers.

These are pure Python dataclasses with no infrastructure dependencies.
They are the integration contract between ingestion, RAG, LLM, and query layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResponseFormat(str, Enum):
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    DETAILED_RESPONSE = "DETAILED_RESPONSE"


@dataclass
class Chunk:
    """
    A text chunk ready for embedding and storage in the vector store.

    chunk_id is used for idempotent re-ingestion: delete-before-reinsert by doc_id.
    allowed_roles contains role UUIDs (as strings) that may access this chunk.
    """

    chunk_id: str          # Stable ID: f"{doc_id}_{page}_{para}_{index}"
    doc_id: str            # UUID of the parent document
    doc_title: str         # Display title for citations
    text: str              # Raw chunk text
    allowed_roles: list[str]  # Role UUIDs (strings); empty = no access
    is_archived: bool = False
    page_number: int | None = None
    para_number: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    """A chunk returned from a similarity search, with distance score."""

    chunk_id: str
    doc_id: str
    doc_title: str
    text: str
    score: float           # Higher = more relevant (1 - cosine distance)
    page_number: int | None = None
    para_number: int | None = None
    is_archived: bool = False


@dataclass
class LLMResponse:
    """Structured response from the LLM layer."""

    content: str
    model_name: str
    retrieved_doc_ids: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class CrossDomainPermissionRequired:
    """
    Typed signal returned by the query engine when zero chunks match after
    role filtering, but the query may be answerable in another domain.

    The caller (API router / notebook) decides how to present the permission prompt.
    The LLM is NOT called when this is returned.
    """

    requested_domain: str | None
    available_domains: list[str]
    message: str = (
        "No policy documents match your current role. "
        "Would you like to search another domain you have access to?"
    )
