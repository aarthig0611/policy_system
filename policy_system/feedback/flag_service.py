"""
Flag service: mark conversations as flagged and snapshot the full thread to log.

Triggered automatically when thumbs-down (rating < 3) feedback is submitted.
The snapshot is written to a structured log for offline analysis.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policy_system.db.models import Conversation, Message

logger = logging.getLogger(__name__)


async def flag_conversation(
    session: AsyncSession,
    conv_id: uuid.UUID,
    reason: str = "negative_feedback",
) -> Conversation:
    """
    Set is_flagged=True on a conversation and snapshot the full thread to log.

    Raises ValueError if the conversation is not found.
    """
    conv = await session.get(Conversation, conv_id)
    if conv is None:
        raise ValueError(f"Conversation {conv_id} not found")

    conv.is_flagged = True

    # Fetch full message thread for snapshot
    messages_result = await session.execute(
        select(Message)
        .where(Message.conv_id == conv_id)
        .order_by(Message.created_at)
    )
    messages = list(messages_result.scalars().all())

    # Write snapshot to structured log
    snapshot = {
        "flagged_at": datetime.now(timezone.utc).isoformat(),
        "conv_id": str(conv_id),
        "user_id": str(conv.user_id),
        "reason": reason,
        "messages": [
            {
                "msg_id": str(m.msg_id),
                "role": m.role.value,
                "content": m.content,
                "format_used": m.format_used.value,
                "retrieved_doc_ids": m.retrieved_doc_ids,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }

    logger.warning(
        "Conversation flagged: %s | reason=%s | messages=%d",
        conv_id,
        reason,
        len(messages),
        extra={"snapshot": snapshot},
    )

    # Also write to a local JSONL file for easy offline analysis
    _write_snapshot_to_file(snapshot)

    return conv


def _write_snapshot_to_file(snapshot: dict) -> None:
    """Append snapshot to a JSONL file in the data directory."""
    try:
        log_dir = Path("./data")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "flagged_conversations.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot) + "\n")
    except Exception as exc:
        logger.error("Failed to write flagged conversation snapshot: %s", exc)


async def get_flagged_conversations(
    session: AsyncSession,
    limit: int = 50,
) -> list[Conversation]:
    """Return the most recently flagged conversations."""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.is_flagged == True)  # noqa: E712
        .order_by(Conversation.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
