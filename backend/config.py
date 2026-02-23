"""
Application configuration via pydantic-settings.

All settings are read from environment variables or a .env file.
Swap RAG_PROVIDER / LLM_PROVIDER values to change implementations without
touching any other code.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://policy_user:policy_pass@localhost:5432/policy_db"

    # JWT
    jwt_secret: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "policy_chunks"

    # File storage
    upload_dir: str = "./data/uploads"

    # Provider selection (swap to change implementations)
    rag_provider: str = "chromadb"
    llm_provider: str = "ollama"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Chunking defaults
    chunk_size: int = 800
    chunk_overlap: int = 100

    # RAG retrieval
    rag_top_k: int = 5


# Singleton — import this everywhere
settings = Settings()
