"""Admin service: user creation, role assignment, and listing."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from policy_system.auth.password import hash_password
from policy_system.core.exceptions import UserNotFoundError, RoleNotFoundError, ValidationError
from policy_system.db.models import Role, ResponseFormat, User, UserRole


async def create_user(
    session: AsyncSession,
    email: str,
    password: str,
    default_format: ResponseFormat = ResponseFormat.EXECUTIVE_SUMMARY,
) -> User:
    """
    Create a new user with a hashed password.

    Raises ValidationError if the email already exists.
    """
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise ValidationError(f"Email already registered: {email}")

    user = User(
        email=email,
        password_hash=hash_password(password),
        default_format=default_format,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def assign_role(session: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole:
    """
    Assign a role to a user. Idempotent — does nothing if already assigned.

    Raises UserNotFoundError or RoleNotFoundError if either doesn't exist.
    """
    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")

    role = await session.get(Role, role_id)
    if role is None:
        raise RoleNotFoundError(f"Role {role_id} not found")

    existing = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        return existing.scalar_one()

    user_role = UserRole(user_id=user_id, role_id=role_id)
    session.add(user_role)
    await session.flush()
    return user_role


async def remove_role(session: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
    """Remove a role assignment. Returns True if removed, False if not found."""
    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
    )
    user_role = result.scalar_one_or_none()
    if user_role is None:
        return False
    await session.delete(user_role)
    return True


async def list_users(session: AsyncSession) -> list[User]:
    """Return all users with their roles eagerly loaded."""
    result = await session.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetch a user by email. Returns None if not found."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def deactivate_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    """Soft-disable a user by setting is_active=False."""
    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")
    user.is_active = False
    return user
