"""
Ollama LLM provider implementing the LLMProvider interface.

Handles both text embedding (nomic-embed-text) and chat generation (llama3/mistral).
"""

from __future__ import annotations

import ollama

from backend.config import settings
from backend.core.exceptions import LLMProviderError
from backend.core.models import LLMResponse, RetrievedChunk


class OllamaProvider:
    """Ollama-backed LLMProvider. Fully local inference — no API keys needed."""

    def __init__(
        self,
        base_url: str | None = None,
        embed_model: str | None = None,
        chat_model: str | None = None,
    ) -> None:
        self._base_url = base_url or settings.ollama_base_url
        self._embed_model = embed_model or settings.ollama_embed_model
        self._chat_model = chat_model or settings.ollama_chat_model
        self._client = ollama.Client(host=self._base_url)

    def embed(self, text: str) -> list[float]:
        """Return embedding vector for a single text string."""
        try:
            response = self._client.embeddings(model=self._embed_model, prompt=text)
            return response["embedding"]
        except Exception as exc:
            raise LLMProviderError(f"Ollama embed failed: {exc}") from exc

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""
        embeddings = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list[RetrievedChunk],
        stream: bool = False,
    ) -> LLMResponse:
        """
        Generate a grounded response using the provided context chunks.

        The context chunks are formatted into the user message as a numbered
        list so the model can reference them in its response.

        Note: This method should NOT be called when context_chunks is empty.
        The query engine handles the CrossDomainPermissionRequired case before
        calling chat().
        """
        if not context_chunks:
            raise LLMProviderError(
                "chat() called with empty context_chunks. "
                "The query engine should handle the empty-context case before calling chat()."
            )

        # Build context block
        context_lines = []
        for i, chunk in enumerate(context_chunks, start=1):
            location = f"[Doc: {chunk.doc_title}"
            if chunk.page_number is not None:
                location += f", Page {chunk.page_number}"
            if chunk.para_number is not None:
                location += f", Para {chunk.para_number}"
            location += "]"
            context_lines.append(f"[{i}] {location}\n{chunk.text}")

        context_block = "\n\n---\n\n".join(context_lines)

        full_user_message = (
            f"Context from policy documents:\n\n{context_block}\n\n"
            f"---\n\nQuestion: {user_message}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_message},
        ]

        try:
            response = self._client.chat(
                model=self._chat_model,
                messages=messages,
                stream=False,
            )
        except Exception as exc:
            raise LLMProviderError(f"Ollama chat failed: {exc}") from exc

        content = response["message"]["content"]
        doc_ids = list({chunk.doc_id for chunk in context_chunks})

        return LLMResponse(
            content=content,
            model_name=self._chat_model,
            retrieved_doc_ids=doc_ids,
            prompt_tokens=response.get("prompt_eval_count", 0),
            completion_tokens=response.get("eval_count", 0),
        )

    def health_check(self) -> bool:
        """Return True if the Ollama service is reachable and models are available."""
        try:
            models = self._client.list()
            model_names = [m["name"] for m in models.get("models", [])]
            has_embed = any(self._embed_model in name for name in model_names)
            has_chat = any(self._chat_model in name for name in model_names)
            return has_embed and has_chat
        except Exception:
            return False
