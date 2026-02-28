"""Shared singleton RAG + LLM providers.

Ensures only one ChromaDB client is created per process — required because
ChromaDB in embedded mode is not safe for multiple simultaneous clients.
"""

from __future__ import annotations

from backend.core.interfaces import LLMProvider, RAGProvider

_rag_provider: RAGProvider | None = None
_llm_provider: LLMProvider | None = None


def get_providers() -> tuple[RAGProvider, LLMProvider]:
    """Return the (rag, llm) provider singletons, initialising on first call."""
    global _rag_provider, _llm_provider
    if _rag_provider is None:
        from backend.rag.factory import get_rag_provider
        _rag_provider = get_rag_provider()
    if _llm_provider is None:
        from backend.llm.factory import get_llm_provider
        _llm_provider = get_llm_provider()
    return _rag_provider, _llm_provider
