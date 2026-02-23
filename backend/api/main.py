"""
FastAPI application factory with CORS, lifespan hooks, and all routers mounted.

IMPORTANT: Run with --workers 1 (single process) due to ChromaDB embedded mode constraint.
Multi-worker deployment requires migrating to pgvector.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routers import admin, auth, feedback, query
from backend.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    logger.info("Policy System starting up...")
    logger.info("RAG provider: %s", settings.rag_provider)
    logger.info("LLM provider: %s | model: %s", settings.llm_provider, settings.ollama_chat_model)
    logger.info("ChromaDB persist dir: %s", settings.chroma_persist_dir)
    logger.warning(
        "Single-worker mode enforced: ChromaDB embedded is not safe with multiple workers."
    )

    yield

    logger.info("Policy System shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Policy System API",
        description=(
            "Role-based AI policy management system with RAG retrieval. "
            "Run with --workers 1 (ChromaDB single-process constraint)."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS — allow Next.js dev server and any configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global error handler — return JSON for unhandled exceptions
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # Mount routers
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(query.router)
    app.include_router(feedback.router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Basic health check endpoint."""
        return {"status": "ok", "version": "0.1.0"}

    return app


# Module-level app instance for uvicorn
app = create_app()
