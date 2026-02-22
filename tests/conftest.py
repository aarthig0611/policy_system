"""Pytest fixtures shared across all tests."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from policy_system.api.main import create_app
from policy_system.auth.password import hash_password
from policy_system.db.base import Base
from policy_system.db.models import ResponseFormat, Role, RoleType, User, UserRole
from policy_system.db.session import get_db_session

# In-memory SQLite for tests (dialect-agnostic testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session that rolls back after each test."""
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def admin_user(session: AsyncSession) -> User:
    """Create a system admin user for tests."""
    role = Role(role_name="test_admin", role_type=RoleType.SYSTEM_ADMIN, domain=None)
    session.add(role)
    await session.flush()

    user = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("adminpassword"),
        default_format=ResponseFormat.EXECUTIVE_SUMMARY,
    )
    session.add(user)
    await session.flush()

    session.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    await session.flush()
    return user


@pytest_asyncio.fixture
async def regular_user(session: AsyncSession) -> User:
    """Create a regular functional user for tests."""
    role = Role(
        role_name=f"it_eng_{uuid.uuid4().hex[:6]}",
        role_type=RoleType.FUNCTIONAL,
        domain="IT",
    )
    session.add(role)
    await session.flush()

    user = User(
        email=f"user_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("userpassword"),
        default_format=ResponseFormat.EXECUTIVE_SUMMARY,
    )
    session.add(user)
    await session.flush()

    session.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    await session.flush()
    return user


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with the test DB session injected."""
    app = create_app()

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
