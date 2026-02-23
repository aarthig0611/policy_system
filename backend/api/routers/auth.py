"""Auth router: login endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.admin.user_service import get_user_by_email
from backend.api.schemas import LoginRequest, TokenResponse, UserResponse
from backend.auth.dependencies import get_current_user
from backend.auth.jwt_handler import create_token
from backend.auth.password import verify_password
from backend.db.models import User, UserRole
from backend.db.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Exchange email + password for a JWT access token."""
    user = await get_user_by_email(session, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    token = create_token(str(user.user_id), user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        default_format=user.default_format,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    roles = []
    for ur in current_user.roles:
        if ur.role:
            from backend.api.schemas import RoleResponse
            roles.append(RoleResponse.model_validate(ur.role))
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        default_format=current_user.default_format,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        roles=roles,
    )
