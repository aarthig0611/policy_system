"""
Abstract interfaces for pluggable RAG and LLM providers.

Uses typing.Protocol (structural subtyping) — concrete implementations do NOT
need to import from core/. Swapping providers requires only changing config.py.

Security invariant: similarity_search MUST apply allowed_roles and is_archived
as pre-filters at the DB/vector-store level — never as post-filters.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from policy_system.core.models import Chunk, LLMResponse, RetrievedChunk


@runtime_checkable
class RAGProvider(Protocol):
    """Vector store interface for document chunks."""

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Embed and store chunks. Uses chunk.chunk_id for idempotent re-ingestion."""
        ...

    def similarity_search(
        self,
        query_embedding: list[float],
        allowed_role_ids: list[str],
        top_k: int = 5,
        include_archived: bool = False,
    ) -> list[RetrievedChunk]:
        """
        Return top_k chunks matching the query.

        SECURITY: allowed_roles and is_archived filtering MUST happen at the
        vector store level (pre-filter), not in Python after retrieval.
        """
        ...

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks for a document. Returns count deleted."""
        ...

    def update_archived_status(self, doc_id: str, is_archived: bool) -> int:
        """Update is_archived metadata flag for all chunks of a document. Returns count updated."""
        ...

    def get_chunk_count(self) -> int:
        """Return total number of chunks stored."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """LLM interface for embedding and chat generation."""

    def embed(self, text: str) -> list[float]:
        """Return embedding vector for a single text string."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""
        ...

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list[RetrievedChunk],
        stream: bool = False,
    ) -> LLMResponse:
        """
        Generate a grounded response using the provided context chunks.

        The implementation must NOT call the LLM if context_chunks is empty —
        the query engine handles that case before calling chat().
        """
        ...

    def health_check(self) -> bool:
        """Return True if the LLM service is reachable and ready."""
        ...
