"""
Query engine: the main orchestrator for policy queries.

Pipeline:
  1. Resolve user's allowed role IDs (SQL access filter)
  2. Embed the query (LLM provider)
  3. Retrieve relevant chunks (RAG provider — security pre-filter applied here)
  4. If zero chunks: return CrossDomainPermissionRequired (DO NOT call LLM)
  5. Generate response (LLM provider)
  6. Build citations (Detailed mode only)
  7. Persist conversation + messages

Security invariant: step 3's pre-filter is the security boundary.
The engine never bypasses or post-filters the RAG results.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.interfaces import LLMProvider, RAGProvider
from backend.core.models import CrossDomainPermissionRequired, RetrievedChunk
from backend.db.models import ResponseFormat, User
from backend.query.access_filter import get_allowed_role_ids, get_user_domains
from backend.query.citation_builder import build_citations
from backend.query.conversation_service import (
    get_or_create_conversation,
    save_assistant_message,
    save_user_message,
)
from backend.query.prompts import get_system_prompt


class QueryResult:
    """Structured result from the query engine."""

    def __init__(
        self,
        msg_id: uuid.UUID,
        conv_id: uuid.UUID,
        content: str,
        format_used: ResponseFormat,
        retrieved_chunks: list[RetrievedChunk],
        model_name: str,
    ) -> None:
        self.msg_id = msg_id
        self.conv_id = conv_id
        self.content = content
        self.format_used = format_used
        self.retrieved_chunks = retrieved_chunks
        self.model_name = model_name
        self.retrieved_doc_ids = list({c.doc_id for c in retrieved_chunks})


async def run_query(
    session: AsyncSession,
    rag_provider: RAGProvider,
    llm_provider: LLMProvider,
    user: User,
    message: str,
    format_override: ResponseFormat | None = None,
    include_archived: bool = False,
    domain_filter: str | None = None,
    conv_id: uuid.UUID | None = None,
    top_k: int | None = None,
) -> QueryResult | CrossDomainPermissionRequired:
    """
    Run a policy query for the given user.

    Returns QueryResult on success, or CrossDomainPermissionRequired when no
    chunks match after role filtering (LLM is NOT called in the latter case).
    """
    from backend.config import settings
    from backend.monitoring.metrics import QueryMetricsCollector, persist_metrics, timed

    collector = QueryMetricsCollector(user_id=user.user_id)

    try:
        # 1. Determine response format
        response_format = format_override or user.default_format

        # 2. Resolve allowed role IDs (applies domain_filter if specified)
        allowed_role_ids = await get_allowed_role_ids(
            session, user.user_id, domain_filter=domain_filter
        )

        # 3. Embed the query
        with timed(collector._embed):
            query_embedding = llm_provider.embed(message)

        # 4. Retrieve relevant chunks (SECURITY: pre-filter applied inside RAG provider)
        with timed(collector._retrieve):
            chunks = rag_provider.similarity_search(
                query_embedding=query_embedding,
                allowed_role_ids=allowed_role_ids,
                top_k=top_k or settings.rag_top_k,
                include_archived=include_archived,
                score_threshold=settings.rag_score_threshold,
            )

        collector.chunks_retrieved = len(chunks)

        # 5. If zero chunks: return CrossDomainPermissionRequired — DO NOT call LLM
        if not chunks:
            collector.success = True
            collector.error_type = "cross_domain"
            collector.model_name = settings.ollama_chat_model
            available_domains = await get_user_domains(session, user.user_id)
            return CrossDomainPermissionRequired(
                requested_domain=domain_filter,
                available_domains=available_domains,
            )

        # 6. Get conversation (or start a new one)
        conversation = await get_or_create_conversation(session, user.user_id, conv_id)

        # 7. Save user message
        await save_user_message(session, conversation.conv_id, message, response_format)

        # 8. Generate response
        system_prompt = get_system_prompt(response_format)
        with timed(collector._llm):
            llm_response = llm_provider.chat(
                system_prompt=system_prompt,
                user_message=message,
                context_chunks=chunks,
                cite=(response_format == ResponseFormat.DETAILED_RESPONSE),
            )

        # 9. Save assistant message with source doc IDs
        assistant_msg = await save_assistant_message(
            session,
            conversation.conv_id,
            llm_response.content,
            response_format,
            retrieved_doc_ids=llm_response.retrieved_doc_ids,
        )

        collector.msg_id = assistant_msg.msg_id
        collector.prompt_tokens = llm_response.prompt_tokens
        collector.completion_tokens = llm_response.completion_tokens
        collector.model_name = llm_response.model_name
        collector.success = True

        return QueryResult(
            msg_id=assistant_msg.msg_id,
            conv_id=conversation.conv_id,
            content=llm_response.content,
            format_used=response_format,
            retrieved_chunks=chunks,
            model_name=llm_response.model_name,
        )

    except Exception:
        # timed() already set success=False and error_type on whichever stage failed
        if not collector._embed.success:
            collector.success = False
            collector.error_type = collector._embed.error_type
        elif not collector._retrieve.success:
            collector.success = False
            collector.error_type = collector._retrieve.error_type
        elif not collector._llm.success:
            collector.success = False
            collector.error_type = collector._llm.error_type
        raise

    finally:
        # Always persist — even on exception and even for cross-domain early-return.
        # Python's finally runs before the return value is delivered to the caller.
        await persist_metrics(session, collector)
