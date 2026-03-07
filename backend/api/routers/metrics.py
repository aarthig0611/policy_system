"""Metrics router: aggregate query performance statistics for admins."""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import LatencyStats, MetricsSummary
from backend.auth.dependencies import require_admin
from backend.db.models import QueryMetrics, User
from backend.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/metrics", tags=["metrics"])


def _percentile(values: list[float], p: float) -> float:
    """Return the p-th percentile of a sorted list using nearest-rank method."""
    if not values:
        return 0.0
    idx = max(0, int(len(values) * p / 100) - 1)
    return values[min(idx, len(values) - 1)]


def _latency_stats(values: list[float]) -> LatencyStats:
    """Compute descriptive statistics for a list of latency samples (ms)."""
    if not values:
        return LatencyStats(
            mean_ms=0.0, p50_ms=0.0, p95_ms=0.0,
            p99_ms=0.0, min_ms=0.0, max_ms=0.0,
        )
    s = sorted(values)
    return LatencyStats(
        mean_ms=round(statistics.mean(s), 2),
        p50_ms=round(_percentile(s, 50), 2),
        p95_ms=round(_percentile(s, 95), 2),
        p99_ms=round(_percentile(s, 99), 2),
        min_ms=round(s[0], 2),
        max_ms=round(s[-1], 2),
    )


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    since_hours: int = Query(default=24, ge=1, le=720,
                             description="Look-back window in hours (1–720)"),
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> MetricsSummary:
    """
    Return aggregate performance statistics for query_metrics rows within
    the last `since_hours` hours. Requires SYSTEM_ADMIN role.
    """
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=since_hours)

    result = await session.execute(
        select(QueryMetrics)
        .where(QueryMetrics.created_at >= window_start)
        .order_by(QueryMetrics.created_at)
    )
    rows: list[QueryMetrics] = list(result.scalars().all())

    total = len(rows)
    if total == 0:
        return MetricsSummary(
            total_queries=0,
            successful_queries=0,
            cross_domain_queries=0,
            error_queries=0,
            success_rate=0.0,
            cross_domain_rate=0.0,
            embed_latency=_latency_stats([]),
            retrieve_latency=_latency_stats([]),
            total_latency=_latency_stats([]),
            llm_latency=None,
            avg_chunks_retrieved=0.0,
            avg_prompt_tokens=0.0,
            avg_completion_tokens=0.0,
            avg_total_tokens=0.0,
            window_start=window_start,
            window_end=window_end,
            computed_at=window_end,
        )

    successful = [r for r in rows if r.success and r.error_type != "cross_domain"]
    cross_domain = [r for r in rows if r.error_type == "cross_domain"]
    errors = [r for r in rows if not r.success]
    llm_rows = [r for r in rows if r.llm_latency_ms is not None]

    return MetricsSummary(
        total_queries=total,
        successful_queries=len(successful),
        cross_domain_queries=len(cross_domain),
        error_queries=len(errors),
        success_rate=round(len(successful) / total, 4),
        cross_domain_rate=round(len(cross_domain) / total, 4),
        embed_latency=_latency_stats([r.embed_latency_ms for r in rows]),
        retrieve_latency=_latency_stats([r.retrieve_latency_ms for r in rows]),
        total_latency=_latency_stats([r.total_latency_ms for r in rows]),
        llm_latency=_latency_stats([r.llm_latency_ms for r in llm_rows]) if llm_rows else None,
        avg_chunks_retrieved=round(sum(r.chunks_retrieved for r in rows) / total, 2),
        avg_prompt_tokens=round(sum(r.prompt_tokens for r in rows) / total, 2),
        avg_completion_tokens=round(sum(r.completion_tokens for r in rows) / total, 2),
        avg_total_tokens=round(
            sum(r.prompt_tokens + r.completion_tokens for r in rows) / total, 2
        ),
        window_start=window_start,
        window_end=window_end,
        computed_at=window_end,
    )
