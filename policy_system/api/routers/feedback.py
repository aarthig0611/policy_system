"""Feedback router: thumbs up/down submission with auto-flagging."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from policy_system.api.schemas import FeedbackCreate, FeedbackResponse, MessageResponse
from policy_system.auth.dependencies import get_current_user
from policy_system.core.exceptions import FeedbackError
from policy_system.db.models import Message, User
from policy_system.db.session import get_db_session
from policy_system.feedback import feedback_service, flag_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    """
    Submit feedback (thumbs up/down) for an assistant message.

    - rating 5 = thumbs up
    - rating 1 = thumbs down (requires non-empty comments)
    - Thumbs down automatically flags the conversation for review
    """
    try:
        feedback = await feedback_service.record_feedback(
            session=session,
            msg_id=payload.msg_id,
            rating=payload.rating,
            given_by=current_user.user_id,
            comments=payload.comments,
        )
    except FeedbackError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Auto-flag conversation on thumbs-down
    if payload.rating < 3:
        msg = await session.get(Message, payload.msg_id)
        if msg is not None:
            try:
                await flag_service.flag_conversation(
                    session,
                    msg.conv_id,
                    reason=f"negative_feedback: {payload.comments or '(no comment)'}",
                )
            except Exception:
                pass  # Don't fail the feedback submission if flagging fails

    return FeedbackResponse(
        feedback_id=feedback.feedback_id,
        msg_id=feedback.msg_id,
        rating=feedback.rating,
        comments=feedback.comments,
        weight=feedback.weight,
        created_at=feedback.created_at,
    )


@router.get("/summary/{msg_id}")
async def get_feedback_summary(
    msg_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Get weighted feedback summary for a message."""
    summary = await feedback_service.get_weighted_feedback_summary(session, msg_id)
    return summary
