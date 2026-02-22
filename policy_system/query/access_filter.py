"""
Access filter: resolve a user_id to their allowed role IDs for RAG pre-filtering.

This module bridges the SQL layer (user roles) and the RAG layer (allowed_roles metadata).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policy_system.db.models import Role, RoleType, UserRole


async def get_allowed_role_ids(
    session: AsyncSession,
    user_id: uuid.UUID,
    domain_filter: str | None = None,
) -> list[str]:
    """
    Return a list of role UUIDs (as strings) that the user is authorized for.

    Used as the `allowed_role_ids` argument to RAGProvider.similarity_search().

    Args:
        session: Async database session.
        user_id: The user whose roles we're resolving.
        domain_filter: Optional domain name (e.g., "IT") to restrict to a single domain.
                       Multi-role users can use this to limit scope to one domain.
                       GLOBAL_AUDITOR and SYSTEM_ADMIN roles are always included.

    Returns:
        List of role UUID strings. Empty list = no access.
    """
    result = await session.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .where(UserRole.user_id == user_id)
    )
    roles = list(result.scalars().all())

    if not roles:
        return []

    # Global roles (admin, global auditor) bypass domain filtering
    global_role_types = {RoleType.GLOBAL_AUDITOR, RoleType.SYSTEM_ADMIN}

    filtered = []
    for role in roles:
        if role.role_type in global_role_types:
            filtered.append(role)
        elif domain_filter is None:
            filtered.append(role)
        elif role.domain and role.domain.lower() == domain_filter.lower():
            filtered.append(role)

    return [str(r.role_id) for r in filtered]


async def get_user_domains(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """Return distinct domain names the user has access to (for CrossDomain prompt)."""
    result = await session.execute(
        select(Role.domain)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .where(UserRole.user_id == user_id)
        .where(Role.domain.is_not(None))
        .distinct()
    )
    return [row[0] for row in result.all() if row[0]]
