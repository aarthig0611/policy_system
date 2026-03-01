"""Tests for the query engine and conversation persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.models import CrossDomainPermissionRequired, LLMResponse, RetrievedChunk
from backend.db.models import Conversation, Message, MessageRole, ResponseFormat, Role, RoleType, User, UserRole
from backend.auth.password import hash_password
from backend.query.engine import run_query
from backend.query.conversation_service import get_conversation_messages, get_user_conversations


# ---------------------------------------------------------------------------
# Minimal stub providers — satisfy the Protocol without network calls
# ---------------------------------------------------------------------------

class StubRAGProvider:
    """Returns a fixed set of chunks or nothing, depending on configuration."""

    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self._chunks = chunks or []

    def similarity_search(self, query_embedding, allowed_role_ids, top_k=5, include_archived=False, score_threshold=0.0):
        return self._chunks

    def add_chunks(self, chunks): pass
    def delete_by_doc_id(self, doc_id): return 0
    def update_archived_status(self, doc_id, is_archived): return 0
    def get_chunk_count(self): return len(self._chunks)


class StubLLMProvider:
    """Returns a canned LLM response without any network call."""

    def embed(self, text: str) -> list[float]:
        return [0.1] * 768

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    def chat(self, system_prompt, user_message, context_chunks, stream=False) -> LLMResponse:
        return LLMResponse(
            content="Stub answer based on policy context.",
            model_name="stub-model",
            retrieved_doc_ids=[c.doc_id for c in context_chunks],
        )

    def health_check(self) -> bool:
        return True


def _make_chunk(doc_id: str | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        doc_id=doc_id or str(uuid.uuid4()),
        doc_title="IT Security Policy",
        text="All employees must use MFA.",
        score=0.92,
        page_number=1,
        para_number=0,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def it_user(session: AsyncSession) -> User:
    role = Role(
        role_name=f"it_{uuid.uuid4().hex[:6]}",
        role_type=RoleType.FUNCTIONAL,
        domain="IT",
    )
    session.add(role)
    await session.flush()

    user = User(
        email=f"it_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass"),
        default_format=ResponseFormat.EXECUTIVE_SUMMARY,
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    await session.flush()
    return user


# ---------------------------------------------------------------------------
# Query engine tests
# ---------------------------------------------------------------------------

class TestRunQuery:
    async def test_returns_query_result_when_chunks_match(self, session: AsyncSession, it_user: User):
        rag = StubRAGProvider(chunks=[_make_chunk()])
        llm = StubLLMProvider()

        result = await run_query(
            session=session,
            rag_provider=rag,
            llm_provider=llm,
            user=it_user,
            message="What are the MFA requirements?",
        )

        assert not isinstance(result, CrossDomainPermissionRequired)
        assert result.content == "Stub answer based on policy context."
        assert result.conv_id is not None
        assert result.msg_id is not None

    async def test_returns_cross_domain_when_no_chunks(self, session: AsyncSession, it_user: User):
        rag = StubRAGProvider(chunks=[])   # zero chunks → blocked
        llm = StubLLMProvider()

        result = await run_query(
            session=session,
            rag_provider=rag,
            llm_provider=llm,
            user=it_user,
            message="What are the vendor payment terms?",
        )

        assert isinstance(result, CrossDomainPermissionRequired)
        assert isinstance(result.available_domains, list)

    async def test_messages_persisted_after_query(self, session: AsyncSession, it_user: User):
        rag = StubRAGProvider(chunks=[_make_chunk()])
        llm = StubLLMProvider()

        result = await run_query(
            session=session,
            rag_provider=rag,
            llm_provider=llm,
            user=it_user,
            message="What is the password policy?",
        )

        messages = await get_conversation_messages(session, result.conv_id)
        assert len(messages) == 2
        assert messages[0].role == MessageRole.user
        assert messages[0].content == "What is the password policy?"
        assert messages[1].role == MessageRole.assistant
        assert messages[1].content == "Stub answer based on policy context."

    async def test_follow_up_continues_same_conversation(self, session: AsyncSession, it_user: User):
        rag = StubRAGProvider(chunks=[_make_chunk()])
        llm = StubLLMProvider()

        result1 = await run_query(
            session=session,
            rag_provider=rag,
            llm_provider=llm,
            user=it_user,
            message="What is MFA?",
        )

        result2 = await run_query(
            session=session,
            rag_provider=rag,
            llm_provider=llm,
            user=it_user,
            message="Any exceptions?",
            conv_id=result1.conv_id,
        )

        assert result2.conv_id == result1.conv_id
        messages = await get_conversation_messages(session, result1.conv_id)
        assert len(messages) == 4  # 2 user + 2 assistant

    async def test_format_override_applied(self, session: AsyncSession, it_user: User):
        rag = StubRAGProvider(chunks=[_make_chunk()])
        llm = StubLLMProvider()

        result = await run_query(
            session=session,
            rag_provider=rag,
            llm_provider=llm,
            user=it_user,
            message="Explain data classification.",
            format_override=ResponseFormat.DETAILED_RESPONSE,
        )

        assert result.format_used == ResponseFormat.DETAILED_RESPONSE

    async def test_llm_not_called_when_no_chunks(self, session: AsyncSession, it_user: User):
        """Verifies the security invariant: LLM must not be called with zero context."""
        calls = []

        class TrackingLLM(StubLLMProvider):
            def chat(self, system_prompt, user_message, context_chunks, stream=False):
                calls.append(True)
                return super().chat(system_prompt, user_message, context_chunks, stream)

        rag = StubRAGProvider(chunks=[])
        result = await run_query(
            session=session,
            rag_provider=rag,
            llm_provider=TrackingLLM(),
            user=it_user,
            message="Tell me about finances.",
        )

        assert isinstance(result, CrossDomainPermissionRequired)
        assert len(calls) == 0, "LLM must not be called when zero chunks matched"


# ---------------------------------------------------------------------------
# Conversation service tests
# ---------------------------------------------------------------------------

class TestConversationService:
    async def test_get_user_conversations_returns_both(self, session: AsyncSession, it_user: User):
        rag = StubRAGProvider(chunks=[_make_chunk()])
        llm = StubLLMProvider()

        r1 = await run_query(session=session, rag_provider=rag, llm_provider=llm,
                             user=it_user, message="First question")
        r2 = await run_query(session=session, rag_provider=rag, llm_provider=llm,
                             user=it_user, message="Second question")

        convs = await get_user_conversations(session, it_user.user_id)
        conv_ids = [c.conv_id for c in convs]

        assert r1.conv_id in conv_ids
        assert r2.conv_id in conv_ids
        assert len(conv_ids) >= 2
