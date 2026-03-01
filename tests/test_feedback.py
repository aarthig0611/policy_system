"""Tests for the feedback service and feedback API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_handler import create_token
from backend.auth.password import hash_password
from backend.core.exceptions import FeedbackError
from backend.db.models import (
    Conversation,
    Feedback,
    Message,
    MessageRole,
    ResponseFormat,
    Role,
    RoleType,
    User,
    UserRole,
)
from backend.feedback import feedback_service, flag_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

async def _make_user_with_role(session: AsyncSession, role_type: RoleType) -> User:
    role = Role(
        role_name=f"role_{uuid.uuid4().hex[:6]}",
        role_type=role_type,
        domain="IT" if role_type != RoleType.GLOBAL_AUDITOR else None,
    )
    session.add(role)
    await session.flush()

    user = User(
        email=f"u_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass"),
        default_format=ResponseFormat.EXECUTIVE_SUMMARY,
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    await session.flush()
    return user


async def _make_message(session: AsyncSession, user: User) -> Message:
    conv = Conversation(user_id=user.user_id)
    session.add(conv)
    await session.flush()

    msg = Message(
        conv_id=conv.conv_id,
        role=MessageRole.assistant,
        content="Policy says: use MFA.",
        format_used=ResponseFormat.EXECUTIVE_SUMMARY,
    )
    session.add(msg)
    await session.flush()
    return msg


@pytest.fixture
async def functional_user(session: AsyncSession) -> User:
    return await _make_user_with_role(session, RoleType.FUNCTIONAL)


@pytest.fixture
async def domain_auditor(session: AsyncSession) -> User:
    return await _make_user_with_role(session, RoleType.DOMAIN_AUDITOR)


@pytest.fixture
async def global_auditor(session: AsyncSession) -> User:
    return await _make_user_with_role(session, RoleType.GLOBAL_AUDITOR)


@pytest.fixture
async def assistant_message(session: AsyncSession, functional_user: User) -> Message:
    return await _make_message(session, functional_user)


# ---------------------------------------------------------------------------
# Feedback weight tests
# ---------------------------------------------------------------------------

class TestFeedbackWeights:
    async def test_functional_user_weight_is_1(
        self, session: AsyncSession, functional_user: User, assistant_message: Message
    ):
        fb = await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=5, given_by=functional_user.user_id
        )
        assert fb.weight == 1.0

    async def test_domain_auditor_weight_is_1_5(
        self, session: AsyncSession, domain_auditor: User, assistant_message: Message
    ):
        fb = await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=5, given_by=domain_auditor.user_id
        )
        assert fb.weight == 1.5

    async def test_global_auditor_weight_is_2(
        self, session: AsyncSession, global_auditor: User, assistant_message: Message
    ):
        fb = await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=5, given_by=global_auditor.user_id
        )
        assert fb.weight == 2.0


# ---------------------------------------------------------------------------
# Thumbs-down validation
# ---------------------------------------------------------------------------

class TestThumbsDown:
    async def test_thumbs_down_without_comment_raises(
        self, session: AsyncSession, functional_user: User, assistant_message: Message
    ):
        with pytest.raises(FeedbackError, match="Comments are required"):
            await feedback_service.record_feedback(
                session, assistant_message.msg_id, rating=1,
                given_by=functional_user.user_id, comments=None
            )

    async def test_thumbs_down_with_empty_string_raises(
        self, session: AsyncSession, functional_user: User, assistant_message: Message
    ):
        with pytest.raises(FeedbackError, match="Comments are required"):
            await feedback_service.record_feedback(
                session, assistant_message.msg_id, rating=1,
                given_by=functional_user.user_id, comments=""
            )

    async def test_thumbs_down_with_comment_succeeds(
        self, session: AsyncSession, functional_user: User, assistant_message: Message
    ):
        fb = await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=1,
            given_by=functional_user.user_id,
            comments="Response was missing key details.",
        )
        assert fb.rating == 1
        assert fb.comments == "Response was missing key details."

    async def test_thumbs_down_flags_conversation(
        self, session: AsyncSession, functional_user: User, assistant_message: Message
    ):
        await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=1,
            given_by=functional_user.user_id,
            comments="Incorrect answer.",
        )
        conv = await flag_service.flag_conversation(
            session, assistant_message.conv_id, reason="negative_feedback"
        )
        assert conv.is_flagged is True


# ---------------------------------------------------------------------------
# Weighted aggregation
# ---------------------------------------------------------------------------

class TestWeightedAggregation:
    async def test_weighted_avg_single_response(
        self, session: AsyncSession, functional_user: User, assistant_message: Message
    ):
        await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=5, given_by=functional_user.user_id
        )
        summary = await feedback_service.get_weighted_feedback_summary(
            session, assistant_message.msg_id
        )
        assert summary["total_responses"] == 1
        assert summary["avg_rating"] == 5.0
        assert summary["weighted_avg"] == 5.0

    async def test_weighted_avg_auditor_outweighs_functional(
        self, session: AsyncSession, functional_user: User,
        global_auditor: User, assistant_message: Message
    ):
        # Functional gives 1, auditor gives 5 (weight=2.0)
        # weighted_avg = (1*1.0 + 5*2.0) / (1.0 + 2.0) = 11/3 ≈ 3.67
        await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=1,
            given_by=functional_user.user_id, comments="Not helpful."
        )
        await feedback_service.record_feedback(
            session, assistant_message.msg_id, rating=5,
            given_by=global_auditor.user_id,
        )
        summary = await feedback_service.get_weighted_feedback_summary(
            session, assistant_message.msg_id
        )
        assert summary["total_responses"] == 2
        assert abs(summary["weighted_avg"] - (11 / 3)) < 0.01

    async def test_no_feedback_returns_zero(
        self, session: AsyncSession, assistant_message: Message
    ):
        summary = await feedback_service.get_weighted_feedback_summary(
            session, assistant_message.msg_id
        )
        assert summary["total_responses"] == 0
        assert summary["weighted_avg"] == 0.0


# ---------------------------------------------------------------------------
# Feedback API endpoint tests
# ---------------------------------------------------------------------------

class TestFeedbackAPI:
    async def test_submit_thumbs_up_returns_201(
        self, client: AsyncClient, session: AsyncSession,
        functional_user: User, assistant_message: Message
    ):
        token = create_token(str(functional_user.user_id), functional_user.email)
        resp = await client.post(
            "/feedback/",
            json={"msg_id": str(assistant_message.msg_id), "rating": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["rating"] == 5
        assert data["weight"] == 1.0

    async def test_submit_thumbs_down_no_comment_returns_422(
        self, client: AsyncClient, session: AsyncSession,
        functional_user: User, assistant_message: Message
    ):
        token = create_token(str(functional_user.user_id), functional_user.email)
        resp = await client.post(
            "/feedback/",
            json={"msg_id": str(assistant_message.msg_id), "rating": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_submit_thumbs_down_with_comment_returns_201(
        self, client: AsyncClient, session: AsyncSession,
        functional_user: User, assistant_message: Message
    ):
        token = create_token(str(functional_user.user_id), functional_user.email)
        resp = await client.post(
            "/feedback/",
            json={
                "msg_id": str(assistant_message.msg_id),
                "rating": 1,
                "comments": "Response was incomplete.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    async def test_get_feedback_summary(
        self, client: AsyncClient, session: AsyncSession,
        functional_user: User, assistant_message: Message
    ):
        token = create_token(str(functional_user.user_id), functional_user.email)
        # Submit a rating first
        await client.post(
            "/feedback/",
            json={"msg_id": str(assistant_message.msg_id), "rating": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            f"/feedback/summary/{assistant_message.msg_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_responses"] >= 1
        assert "weighted_avg" in data

    async def test_feedback_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/feedback/",
            json={"msg_id": str(uuid.uuid4()), "rating": 5},
        )
        assert resp.status_code == 401
