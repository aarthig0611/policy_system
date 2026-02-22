"""Query router: policy queries with role-filtered RAG retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from policy_system.api.schemas import CrossDomainPrompt, QueryRequest, QueryResponse
from policy_system.auth.dependencies import get_current_user
from policy_system.core.models import CrossDomainPermissionRequired
from policy_system.db.models import User
from policy_system.db.session import get_db_session
from policy_system.llm.factory import get_llm_provider
from policy_system.query.citation_builder import build_citations
from policy_system.query.engine import run_query
from policy_system.rag.factory import get_rag_provider

router = APIRouter(prefix="/query", tags=["query"])

# Module-level providers (initialized once — important for ChromaDB single-process constraint)
_rag_provider = None
_llm_provider = None


def _get_providers():
    global _rag_provider, _llm_provider
    if _rag_provider is None:
        _rag_provider = get_rag_provider()
    if _llm_provider is None:
        _llm_provider = get_llm_provider()
    return _rag_provider, _llm_provider


@router.post("/", response_model=QueryResponse | CrossDomainPrompt)
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
    rag_provider, llm_provider = _get_providers()

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
        citations=citations if result.format_used.value == "DETAILED_RESPONSE" else [],
        retrieved_doc_ids=result.retrieved_doc_ids,
    )
