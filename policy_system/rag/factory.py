"""RAG provider factory — returns implementation from config."""

from __future__ import annotations

from policy_system.config import settings
from policy_system.core.interfaces import RAGProvider


def get_rag_provider() -> RAGProvider:
    """Return the configured RAGProvider implementation."""
    if settings.rag_provider == "chromadb":
        from policy_system.rag.chromadb_provider import ChromaDBProvider
        return ChromaDBProvider()
    raise ValueError(f"Unknown RAG provider: {settings.rag_provider}. Valid: chromadb")
