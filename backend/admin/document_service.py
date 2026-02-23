"""Admin service: document registration and archive management."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.exceptions import DocumentNotFoundError
from backend.db.models import Document, DocumentAccess


async def register_document(
    session: AsyncSession,
    title: str,
    storage_uri: str,
    uploaded_by: uuid.UUID | None = None,
) -> Document:
    """
    Register document metadata in the database.

    Does NOT trigger ingestion or embedding — that's handled by the ingestion pipeline.
    Role access is set separately via set_document_access().
    """
    doc = Document(
        title=title,
        storage_uri=storage_uri,
        uploaded_by=uploaded_by,
        is_archived=False,
    )
    session.add(doc)
    await session.flush()
    return doc


async def archive_document(session: AsyncSession, doc_id: uuid.UUID) -> Document:
    """Mark a document as archived. Raises DocumentNotFoundError if not found."""
    doc = await session.get(Document, doc_id)
    if doc is None:
        raise DocumentNotFoundError(f"Document {doc_id} not found")
    doc.is_archived = True
    return doc


async def unarchive_document(session: AsyncSession, doc_id: uuid.UUID) -> Document:
    """Unarchive a document. Raises DocumentNotFoundError if not found."""
    doc = await session.get(Document, doc_id)
    if doc is None:
        raise DocumentNotFoundError(f"Document {doc_id} not found")
    doc.is_archived = False
    return doc


async def get_document(session: AsyncSession, doc_id: uuid.UUID) -> Document | None:
    """Fetch a document by ID with access roles eagerly loaded."""
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.access_roles).selectinload(DocumentAccess.role))
        .where(Document.doc_id == doc_id)
    )
    return result.scalar_one_or_none()


async def list_documents(
    session: AsyncSession, include_archived: bool = False
) -> list[Document]:
    """List all documents, optionally including archived ones."""
    query = select(Document).options(
        selectinload(Document.access_roles).selectinload(DocumentAccess.role)
    )
    if not include_archived:
        query = query.where(Document.is_archived == False)  # noqa: E712
    query = query.order_by(Document.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())
