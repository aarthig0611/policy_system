"""Query router: policy queries with role-filtered RAG retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from backend.api.providers import get_providers
from backend.api.schemas import (
    ChatMessageResponse,
    ConversationResponse,
    CrossDomainPrompt,
    QueryRequest,
    QueryResponse,
)
from backend.auth.dependencies import get_current_user
from backend.core.models import CrossDomainPermissionRequired
from backend.db.models import Conversation, MessageRole, ResponseFormat, User
from backend.db.session import get_db_session
from backend.query.citation_builder import build_citations
from backend.query.conversation_service import get_conversation_messages, get_user_conversations
from backend.query.engine import run_query

router = APIRouter(prefix="/query", tags=["query"], redirect_slashes=False)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ConversationResponse]:
    """List the current user's conversations, most recent first."""
    convs = await get_user_conversations(session, current_user.user_id)
    result = []
    for c in convs:
        # messages are already eager-loaded; find the first user message for the preview
        first_user = next(
            (m for m in sorted(c.messages, key=lambda m: m.created_at)
             if m.role == MessageRole.user),
            None,
        )
        result.append(
            ConversationResponse(
                conv_id=c.conv_id,
                user_id=c.user_id,
                is_flagged=c.is_flagged,
                started_at=c.started_at,
                message_count=len(c.messages),
                first_user_message=first_user.content if first_user else None,
            )
        )
    return result


@router.get("/conversations/{conv_id}/messages", response_model=list[ChatMessageResponse])
async def list_conversation_messages(
    conv_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessageResponse]:
    """Return all messages in a conversation. Only accessible by the conversation owner."""
    conv = await session.get(Conversation, conv_id)
    if conv is None or conv.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    messages = await get_conversation_messages(session, conv_id)
    return [
        ChatMessageResponse(
            msg_id=m.msg_id,
            conv_id=m.conv_id,
            role=m.role.value,
            content=m.content,
            format_used=m.format_used,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("", response_model=QueryResponse | CrossDomainPrompt)
async def query_policy(
    payload: QueryRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a policy query. Returns a grounded, role-filtered response.

    If no documents match the user's roles, returns a CrossDomainPrompt
    instead of calling the LLM.
    """
    rag_provider, llm_provider = get_providers()

    result = await run_query(
        session=session,
        rag_provider=rag_provider,
        llm_provider=llm_provider,
        user=current_user,
        message=payload.message,
        format_override=payload.format_override,
        include_archived=payload.include_archived,
        domain_filter=payload.domain_filter,
        conv_id=payload.conv_id,
    )

    if isinstance(result, CrossDomainPermissionRequired):
        return CrossDomainPrompt(
            message=result.message,
            available_domains=result.available_domains,
        )

    citations = build_citations(result.retrieved_chunks)

    return QueryResponse(
        msg_id=result.msg_id,
        conv_id=result.conv_id,
        content=result.content,
        format_used=result.format_used,
        citations=citations if result.format_used == ResponseFormat.DETAILED_RESPONSE else [],
        retrieved_doc_ids=result.retrieved_doc_ids,
    )
