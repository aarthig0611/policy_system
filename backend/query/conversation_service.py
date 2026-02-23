"""Conversation persistence — create sessions and store messages."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Conversation, Message, MessageRole, ResponseFormat


async def get_or_create_conversation(
    session: AsyncSession,
    user_id: uuid.UUID,
    conv_id: uuid.UUID | None = None,
) -> Conversation:
    """
    Return an existing conversation or create a new one.

    If conv_id is provided and belongs to this user, returns that conversation.
    Otherwise creates a new conversation for the user.
    """
    if conv_id is not None:
        result = await session.execute(
            select(Conversation).where(
                Conversation.conv_id == conv_id,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv is not None:
            return conv

    conv = Conversation(user_id=user_id)
    session.add(conv)
    await session.flush()
    return conv


async def save_user_message(
    session: AsyncSession,
    conv_id: uuid.UUID,
    content: str,
    format_used: ResponseFormat,
) -> Message:
    """Save the user's query message."""
    msg = Message(
        conv_id=conv_id,
        role=MessageRole.user,
        content=content,
        format_used=format_used,
    )
    session.add(msg)
    await session.flush()
    return msg


async def save_assistant_message(
    session: AsyncSession,
    conv_id: uuid.UUID,
    content: str,
    format_used: ResponseFormat,
    retrieved_doc_ids: list[str] | None = None,
) -> Message:
    """Save the assistant's response message with source doc IDs for citation audit."""
    msg = Message(
        conv_id=conv_id,
        role=MessageRole.assistant,
        content=content,
        format_used=format_used,
        retrieved_doc_ids={"doc_ids": retrieved_doc_ids or []},
    )
    session.add(msg)
    await session.flush()
    return msg


async def get_conversation_messages(
    session: AsyncSession,
    conv_id: uuid.UUID,
) -> list[Message]:
    """Return all messages for a conversation, ordered by creation time."""
    result = await session.execute(
        select(Message)
        .where(Message.conv_id == conv_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def get_user_conversations(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[Conversation]:
    """Return all conversations for a user, most recent first."""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.started_at.desc())
    )
    return list(result.scalars().all())
