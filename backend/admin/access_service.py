"""Admin service: document role access management."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.exceptions import DocumentNotFoundError, RoleNotFoundError
from backend.db.models import Document, DocumentAccess, Role, RoleType, UserRole


async def set_document_access(
    session: AsyncSession,
    doc_id: uuid.UUID,
    role_ids: list[uuid.UUID],
) -> list[DocumentAccess]:
    """
    Replace all access roles for a document with the provided list.

    Idempotent — deletes existing access records then adds new ones.
    Raises DocumentNotFoundError if document doesn't exist.
    """
    doc = await session.get(Document, doc_id)
    if doc is None:
        raise DocumentNotFoundError(f"Document {doc_id} not found")

    # Validate all roles exist
    for role_id in role_ids:
        role = await session.get(Role, role_id)
        if role is None:
            raise RoleNotFoundError(f"Role {role_id} not found")

    # Delete existing access records
    existing = await session.execute(
        select(DocumentAccess).where(DocumentAccess.doc_id == doc_id)
    )
    for access in existing.scalars().all():
        await session.delete(access)

    # Add new access records
    new_records = []
    for role_id in role_ids:
        access = DocumentAccess(doc_id=doc_id, role_id=role_id)
        session.add(access)
        new_records.append(access)

    await session.flush()
    return new_records


async def add_document_access(
    session: AsyncSession, doc_id: uuid.UUID, role_id: uuid.UUID
) -> DocumentAccess:
    """Add a single role to a document's access list. Idempotent."""
    existing = await session.execute(
        select(DocumentAccess).where(
            DocumentAccess.doc_id == doc_id, DocumentAccess.role_id == role_id
        )
    )
    record = existing.scalar_one_or_none()
    if record is not None:
        return record

    access = DocumentAccess(doc_id=doc_id, role_id=role_id)
    session.add(access)
    await session.flush()
    return access


async def get_accessible_docs(
    session: AsyncSession,
    user_id: uuid.UUID,
    include_archived: bool = False,
) -> list[Document]:
    """
    Return all documents accessible to a user based on the UNION of their roles.

    GLOBAL_AUDITOR role grants access to all documents.
    Access is determined by the union of document_access records matching any user role.
    """
    # Get the user's roles
    user_roles_result = await session.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .where(UserRole.user_id == user_id)
    )
    user_roles = list(user_roles_result.scalars().all())

    if not user_roles:
        return []

    # Global Auditor — access to all docs
    is_global_auditor = any(r.role_type == RoleType.GLOBAL_AUDITOR for r in user_roles)

    query = (
        select(Document)
        .options(selectinload(Document.access_roles).selectinload(DocumentAccess.role))
        .distinct()
    )

    if not include_archived:
        query = query.where(Document.is_archived == False)  # noqa: E712

    if not is_global_auditor:
        user_role_ids = [r.role_id for r in user_roles]
        query = (
            query
            .join(DocumentAccess, DocumentAccess.doc_id == Document.doc_id)
            .where(DocumentAccess.role_id.in_(user_role_ids))
        )

    query = query.order_by(Document.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())
