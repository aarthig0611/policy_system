"""
Performance monitoring utilities for the query pipeline.

Usage:
    collector = QueryMetricsCollector(user_id=user.user_id)

    with timed(collector._embed):
        embedding = llm_provider.embed(text)

    with timed(collector._retrieve):
        chunks = rag_provider.similarity_search(...)

    with timed(collector._llm):
        response = llm_provider.chat(...)

    await persist_metrics(session, collector)

Design notes:
- timed() is a synchronous context manager because all three instrumented calls
  (embed, similarity_search, chat) are synchronous even though run_query() is async.
- _TimedResult is pre-allocated so it is readable after the block even if an
  exception occurred (finally always sets latency_ms).
- persist_metrics() catches all internal exceptions and logs them — never propagates
  to the caller, so a metrics write failure never breaks a successful query response.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class _TimedResult:
    """Mutable holder written to by timed() and read by QueryMetricsCollector."""

    latency_ms: float = 0.0
    success: bool = True
    error_type: str | None = None


@contextmanager
def timed(result: _TimedResult) -> Generator[None, None, None]:
    """
    Synchronous context manager that measures wall-clock latency in milliseconds.

    On exception: sets result.success=False, result.error_type to the exception
    class name, then re-raises so the caller's error handling is unaffected.
    latency_ms is always set (in finally), even when an exception occurs.
    """
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        result.success = False
        result.error_type = type(exc).__name__
        raise
    finally:
        result.latency_ms = (time.perf_counter() - start) * 1000.0


@dataclass
class QueryMetricsCollector:
    """
    Accumulates per-stage timing for one run_query() invocation.

    Instantiated at the top of run_query(), populated by timed() calls,
    then passed to persist_metrics() in the finally block.
    """

    user_id: uuid.UUID

    # Per-stage results — pre-allocated so timed() always has a valid target
    _embed: _TimedResult = field(default_factory=_TimedResult)
    _retrieve: _TimedResult = field(default_factory=_TimedResult)
    _llm: _TimedResult = field(default_factory=_TimedResult)

    # Populated after run_query() determines the outcome
    msg_id: uuid.UUID | None = None
    chunks_retrieved: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    success: bool = True
    error_type: str | None = None
    model_name: str = ""

    @property
    def embed_latency_ms(self) -> float:
        return self._embed.latency_ms

    @property
    def retrieve_latency_ms(self) -> float:
        return self._retrieve.latency_ms

    @property
    def llm_latency_ms(self) -> float | None:
        """None when cross-domain (LLM was not called)."""
        if self.error_type == "cross_domain":
            return None
        return self._llm.latency_ms

    @property
    def total_latency_ms(self) -> float:
        return self._embed.latency_ms + self._retrieve.latency_ms + self._llm.latency_ms


async def persist_metrics(
    session: AsyncSession,
    collector: QueryMetricsCollector,
) -> None:
    """
    Persist collected metrics to the query_metrics table.

    Always called in the finally block of run_query() regardless of outcome.
    Any exception is caught and logged — never propagated to the caller.
    """
    from backend.db.models import QueryMetrics  # local import avoids circular dependency

    try:
        row = QueryMetrics(
            user_id=collector.user_id,
            msg_id=collector.msg_id,
            embed_latency_ms=collector.embed_latency_ms,
            retrieve_latency_ms=collector.retrieve_latency_ms,
            llm_latency_ms=collector.llm_latency_ms,
            total_latency_ms=collector.total_latency_ms,
            chunks_retrieved=collector.chunks_retrieved,
            prompt_tokens=collector.prompt_tokens,
            completion_tokens=collector.completion_tokens,
            success=collector.success,
            error_type=collector.error_type,
            model_name=collector.model_name,
            created_at=datetime.now(timezone.utc),
        )
        session.add(row)
        await session.flush()
        logger.debug(
            "Query metrics persisted: total=%.1fms embed=%.1fms retrieve=%.1fms llm=%s success=%s",
            collector.total_latency_ms,
            collector.embed_latency_ms,
            collector.retrieve_latency_ms,
            f"{collector.llm_latency_ms:.1f}ms" if collector.llm_latency_ms is not None else "N/A",
            collector.success,
        )
    except Exception as exc:
        logger.error("Failed to persist query metrics: %s", exc, exc_info=True)
