"""RAG provider factory — returns implementation from config."""

from __future__ import annotations

from backend.config import settings
from backend.core.interfaces import RAGProvider


def get_rag_provider() -> RAGProvider:
    """Return the configured RAGProvider implementation."""
    if settings.rag_provider == "chromadb":
        from backend.rag.chromadb_provider import ChromaDBProvider
        return ChromaDBProvider()
    raise ValueError(f"Unknown RAG provider: {settings.rag_provider}. Valid: chromadb")
