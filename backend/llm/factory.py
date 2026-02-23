"""LLM provider factory — returns implementation from config."""

from __future__ import annotations

from backend.config import settings
from backend.core.interfaces import LLMProvider


def get_llm_provider() -> LLMProvider:
    """Return the configured LLMProvider implementation."""
    if settings.llm_provider == "ollama":
        from backend.llm.ollama_provider import OllamaProvider
        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}. Valid: ollama")
