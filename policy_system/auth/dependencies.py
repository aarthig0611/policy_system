"""FastAPI dependency: extract and validate the current user from Bearer token."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from policy_system.auth.jwt_handler import decode_token
from policy_system.core.exceptions import AuthenticationError
from policy_system.db.models import User, UserRole
from policy_system.db.session import get_db_session

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    FastAPI dependency that:
    1. Extracts the Bearer token from the Authorization header
    2. Decodes and validates the JWT
    3. Fetches and returns the User ORM object

    Raises HTTP 401 if any step fails.
    """
    try:
        payload = decode_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (AuthenticationError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    result = await session.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires the current user to have a SYSTEM_ADMIN role."""
    from policy_system.db.models import RoleType

    # Check if any of user's roles is SYSTEM_ADMIN
    has_admin = any(
        ur.role.role_type == RoleType.SYSTEM_ADMIN
        for ur in current_user.roles
        if ur.role is not None
    )
    if not has_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Admin role required",
        )
    return current_user
