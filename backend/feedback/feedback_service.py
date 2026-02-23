"""
Feedback service: record user feedback with auto-computed auditor weight.

Weight rules:
  - GLOBAL_AUDITOR: 2.0
  - DOMAIN_AUDITOR: 1.5
  - FUNCTIONAL / other: 1.0

Thumbs-down (rating < 3) requires a non-empty comment — enforced here AND in the schema.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import FeedbackError
from backend.db.models import Feedback, Message, Role, RoleType, User, UserRole


async def _compute_weight(session: AsyncSession, user_id: uuid.UUID) -> float:
    """Compute feedback weight from the user's highest-privilege role."""
    result = await session.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .where(UserRole.user_id == user_id)
    )
    roles = list(result.scalars().all())

    role_types = {r.role_type for r in roles}

    if RoleType.GLOBAL_AUDITOR in role_types:
        return 2.0
    if RoleType.DOMAIN_AUDITOR in role_types:
        return 1.5
    return 1.0


async def record_feedback(
    session: AsyncSession,
    msg_id: uuid.UUID,
    rating: int,
    given_by: uuid.UUID,
    comments: str | None = None,
) -> Feedback:
    """
    Record feedback for an assistant message.

    Raises FeedbackError if:
      - rating < 3 and comments is empty
      - The message doesn't exist

    Auto-computes weight from the user's role type.
    """
    if rating < 3 and not comments:
        raise FeedbackError("Comments are required for negative feedback (rating < 3)")

    # Verify message exists
    msg = await session.get(Message, msg_id)
    if msg is None:
        raise FeedbackError(f"Message {msg_id} not found")

    weight = await _compute_weight(session, given_by)

    feedback = Feedback(
        msg_id=msg_id,
        given_by=given_by,
        rating=rating,
        comments=comments,
        weight=weight,
    )
    session.add(feedback)
    await session.flush()
    return feedback


async def get_weighted_feedback_summary(
    session: AsyncSession,
    msg_id: uuid.UUID,
) -> dict:
    """
    Compute weighted average rating for a message.

    Returns: {avg_rating, total_responses, weighted_avg}
    """
    result = await session.execute(
        select(
            func.count(Feedback.feedback_id).label("count"),
            func.avg(Feedback.rating).label("avg_rating"),
            func.sum(Feedback.rating * Feedback.weight).label("weighted_sum"),
            func.sum(Feedback.weight).label("weight_sum"),
        ).where(Feedback.msg_id == msg_id)
    )
    row = result.one()

    count = row.count or 0
    avg_rating = float(row.avg_rating) if row.avg_rating else 0.0
    weighted_avg = (
        float(row.weighted_sum) / float(row.weight_sum)
        if row.weight_sum and row.weight_sum > 0
        else 0.0
    )

    return {
        "total_responses": count,
        "avg_rating": avg_rating,
        "weighted_avg": weighted_avg,
    }
