"""Admin router: user management, document management, and role access control."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from backend.admin import access_service, document_service, user_service
from backend.api.providers import get_providers
from backend.ingestion.pipeline import ingest_document
from backend.api.schemas import (
    DocumentAccessUpdate,
    DocumentArchiveToggle,
    DocumentCreate,
    DocumentResponse,
    FlaggedConversationResponse,
    MessageResponse,
    RoleAssign,
    RoleResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from backend.auth.dependencies import get_current_user, require_admin
from backend.core.exceptions import (
    DocumentNotFoundError,
    RoleNotFoundError,
    UserNotFoundError,
    ValidationError,
)
from backend.db.models import Conversation, DocumentAccess, Message, Role, User, UserRole
from backend.db.session import get_db_session

router = APIRouter(prefix="/admin", tags=["admin"])


def _user_to_response(user: User) -> UserResponse:
    roles = []
    for ur in user.roles:
        if ur.role:
            roles.append(RoleResponse.model_validate(ur.role))
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        default_format=user.default_format,
        is_active=user.is_active,
        created_at=user.created_at,
        roles=roles,
    )


def _doc_to_response(doc) -> DocumentResponse:
    roles = []
    for da in doc.access_roles:
        if da.role:
            roles.append(RoleResponse.model_validate(da.role))
    return DocumentResponse(
        doc_id=doc.doc_id,
        title=doc.title,
        storage_uri=doc.storage_uri,
        is_archived=doc.is_archived,
        uploaded_by=doc.uploaded_by,
        created_at=doc.created_at,
        roles=roles,
    )


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Create a new user account. Admin only."""
    try:
        user = await user_service.create_user(
            session, payload.email, payload.password, payload.default_format
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    result = await session.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.user_id == user.user_id)
    )
    return _user_to_response(result.scalar_one())


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> list[UserResponse]:
    """List all users. Admin only."""
    users = await user_service.list_users(session)
    return [_user_to_response(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    users = await user_service.list_users(session)
    user = next((u for u in users if u.user_id == user_id), None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Update user format preference or active status. Admin only."""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.default_format is not None:
        user.default_format = payload.default_format
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await session.flush()
    users = await user_service.list_users(session)
    user = next(u for u in users if u.user_id == user_id)
    return _user_to_response(user)


@router.post("/users/{user_id}/roles", response_model=MessageResponse)
async def assign_role(
    user_id: uuid.UUID,
    payload: RoleAssign,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> MessageResponse:
    """Assign a role to a user. Admin only."""
    try:
        await user_service.assign_role(session, user_id, payload.role_id)
    except (UserNotFoundError, RoleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageResponse(message="Role assigned")


@router.delete("/users/{user_id}/roles/{role_id}", response_model=MessageResponse)
async def remove_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> MessageResponse:
    """Remove a role from a user. Admin only."""
    removed = await user_service.remove_role(session, user_id, role_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
    return MessageResponse(message="Role removed")


# ---------------------------------------------------------------------------
# Role endpoints
# ---------------------------------------------------------------------------


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> list[RoleResponse]:
    """List all roles. Admin only."""
    result = await session.execute(select(Role).order_by(Role.role_name))
    return [RoleResponse.model_validate(r) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# Document endpoints
# ---------------------------------------------------------------------------


_UPLOADS_DIR = Path("data/uploads")
_ACCEPTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=500),
    role_ids: list[uuid.UUID] = Form(...),
    session: AsyncSession = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
) -> DocumentResponse:
    """
    Upload a document file, register it in the DB, and ingest it into ChromaDB.

    Accepts multipart/form-data with:
    - file: the document binary (.pdf / .docx / .txt / .md)
    - title: display title
    - role_ids: repeated form field — one value per role UUID
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ACCEPTED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{suffix}'. Accepted: {', '.join(sorted(_ACCEPTED_SUFFIXES))}",
        )

    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = _UPLOADS_DIR / safe_name
    contents = await file.read()
    dest.write_bytes(contents)

    try:
        doc = await document_service.register_document(
            session,
            title=title.strip(),
            storage_uri=str(dest),
            uploaded_by=current_admin.user_id,
        )
        try:
            await access_service.set_document_access(session, doc.doc_id, role_ids)
        except (DocumentNotFoundError, RoleNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        rag_provider, llm_provider = get_providers()
        allowed_role_strs = [str(r) for r in role_ids]
        ingest_document(
            file_path=dest,
            doc_id=str(doc.doc_id),
            allowed_roles=allowed_role_strs,
            rag_provider=rag_provider,
            llm_provider=llm_provider,
            title=title.strip(),
        )
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    full_doc = await document_service.get_document(session, doc.doc_id)
    return _doc_to_response(full_doc)


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    payload: DocumentCreate,
    session: AsyncSession = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
) -> DocumentResponse:
    """Register a document and assign role access. Admin only."""
    doc = await document_service.register_document(
        session,
        title=payload.title,
        storage_uri=payload.storage_uri,
        uploaded_by=current_admin.user_id,
    )
    try:
        await access_service.set_document_access(session, doc.doc_id, payload.role_ids)
    except (DocumentNotFoundError, RoleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    doc = await document_service.get_document(session, doc.doc_id)
    return _doc_to_response(doc)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    include_archived: bool = False,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> list[DocumentResponse]:
    """List all documents. Admin only."""
    docs = await document_service.list_documents(session, include_archived=include_archived)
    return [_doc_to_response(d) for d in docs]


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> DocumentResponse:
    doc = await document_service.get_document(session, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _doc_to_response(doc)


@router.patch("/documents/{doc_id}/archive", response_model=DocumentResponse)
async def toggle_archive(
    doc_id: uuid.UUID,
    payload: DocumentArchiveToggle,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> DocumentResponse:
    """Archive or unarchive a document. Admin only."""
    try:
        if payload.is_archived:
            await document_service.archive_document(session, doc_id)
        else:
            await document_service.unarchive_document(session, doc_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    doc = await document_service.get_document(session, doc_id)
    return _doc_to_response(doc)


@router.put("/documents/{doc_id}/access", response_model=MessageResponse)
async def set_document_access(
    doc_id: uuid.UUID,
    payload: DocumentAccessUpdate,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> MessageResponse:
    """Replace all access roles for a document. Admin only."""
    try:
        await access_service.set_document_access(session, doc_id, payload.role_ids)
    except (DocumentNotFoundError, RoleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageResponse(message="Document access updated")


# ---------------------------------------------------------------------------
# Flagged conversation endpoints
# ---------------------------------------------------------------------------


@router.get("/flagged-conversations", response_model=list[FlaggedConversationResponse])
async def list_flagged_conversations(
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> list[FlaggedConversationResponse]:
    """List all flagged conversations with user email and first message preview. Admin only."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(Conversation)
        .where(Conversation.is_flagged == True)  # noqa: E712
        .options(
            selectinload(Conversation.user),
            selectinload(Conversation.messages),
        )
        .order_by(Conversation.started_at.desc())
    )
    convs = result.scalars().all()

    items = []
    for conv in convs:
        first_msg = next(
            (m.content for m in conv.messages if m.role.value == "user"),
            None,
        )
        items.append(
            FlaggedConversationResponse(
                conv_id=conv.conv_id,
                user_email=conv.user.email if conv.user else "unknown",
                first_message=first_msg[:200] if first_msg else None,
                started_at=conv.started_at,
                message_count=len(conv.messages),
            )
        )
    return items


@router.patch(
    "/flagged-conversations/{conv_id}",
    response_model=MessageResponse,
)
async def resolve_flagged_conversation(
    conv_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> MessageResponse:
    """Clear the is_flagged flag on a conversation (mark as resolved). Admin only."""
    conv = await session.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv.is_flagged = False
    await session.flush()
    return MessageResponse(message="Conversation resolved")
