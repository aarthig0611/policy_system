"""Tests for admin services — user management, document registration, access control."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.admin import access_service, document_service, user_service
from backend.core.exceptions import ValidationError
from backend.db.models import ResponseFormat, Role, RoleType, User, UserRole


@pytest.mark.asyncio
class TestUserService:
    async def test_create_user(self, session: AsyncSession):
        user = await user_service.create_user(
            session, "newuser@test.com", "password123"
        )
        assert user.user_id is not None
        assert user.email == "newuser@test.com"
        assert user.password_hash != "password123"
        assert user.is_active is True

    async def test_duplicate_email_raises(self, session: AsyncSession):
        await user_service.create_user(session, "dup@test.com", "password123")
        with pytest.raises(ValidationError):
            await user_service.create_user(session, "dup@test.com", "password123")

    async def test_assign_role(self, session: AsyncSession, regular_user: User):
        role = Role(role_name=f"new_role_{uuid.uuid4().hex[:6]}", role_type=RoleType.FUNCTIONAL, domain="Finance")
        session.add(role)
        await session.flush()

        ur = await user_service.assign_role(session, regular_user.user_id, role.role_id)
        assert ur.user_id == regular_user.user_id
        assert ur.role_id == role.role_id

    async def test_assign_role_idempotent(self, session: AsyncSession, regular_user: User):
        role = Role(role_name=f"idem_role_{uuid.uuid4().hex[:6]}", role_type=RoleType.FUNCTIONAL, domain="IT")
        session.add(role)
        await session.flush()

        ur1 = await user_service.assign_role(session, regular_user.user_id, role.role_id)
        ur2 = await user_service.assign_role(session, regular_user.user_id, role.role_id)
        assert ur1.role_id == ur2.role_id


@pytest.mark.asyncio
class TestDocumentService:
    async def test_register_document(self, session: AsyncSession, admin_user: User):
        doc = await document_service.register_document(
            session,
            title="Test Policy",
            storage_uri="file:///test.pdf",
            uploaded_by=admin_user.user_id,
        )
        assert doc.doc_id is not None
        assert doc.title == "Test Policy"
        assert doc.is_archived is False

    async def test_archive_document(self, session: AsyncSession, admin_user: User):
        doc = await document_service.register_document(
            session, "Archive Test", "file:///archive.pdf", admin_user.user_id
        )
        archived = await document_service.archive_document(session, doc.doc_id)
        assert archived.is_archived is True

    async def test_unarchive_document(self, session: AsyncSession, admin_user: User):
        doc = await document_service.register_document(
            session, "Unarchive Test", "file:///unarchive.pdf", admin_user.user_id
        )
        await document_service.archive_document(session, doc.doc_id)
        restored = await document_service.unarchive_document(session, doc.doc_id)
        assert restored.is_archived is False


@pytest.mark.asyncio
class TestAccessService:
    async def test_set_document_access(self, session: AsyncSession, admin_user: User):
        doc = await document_service.register_document(
            session, "Access Test", "file:///access.pdf", admin_user.user_id
        )
        role = Role(role_name=f"access_role_{uuid.uuid4().hex[:6]}", role_type=RoleType.FUNCTIONAL, domain="IT")
        session.add(role)
        await session.flush()

        records = await access_service.set_document_access(session, doc.doc_id, [role.role_id])
        assert len(records) == 1
        assert records[0].role_id == role.role_id

    async def test_get_accessible_docs_respects_roles(self, session: AsyncSession):
        # Create two users with different roles
        it_role = Role(role_name=f"it_{uuid.uuid4().hex[:6]}", role_type=RoleType.FUNCTIONAL, domain="IT")
        fin_role = Role(role_name=f"fin_{uuid.uuid4().hex[:6]}", role_type=RoleType.FUNCTIONAL, domain="Finance")
        session.add_all([it_role, fin_role])
        await session.flush()

        it_user = await user_service.create_user(session, f"it_{uuid.uuid4().hex[:6]}@test.com", "pass")
        fin_user = await user_service.create_user(session, f"fin_{uuid.uuid4().hex[:6]}@test.com", "pass")
        await user_service.assign_role(session, it_user.user_id, it_role.role_id)
        await user_service.assign_role(session, fin_user.user_id, fin_role.role_id)

        doc = await document_service.register_document(session, "IT Doc", "file:///it.pdf", None)
        await access_service.set_document_access(session, doc.doc_id, [it_role.role_id])

        it_docs = await access_service.get_accessible_docs(session, it_user.user_id)
        fin_docs = await access_service.get_accessible_docs(session, fin_user.user_id)

        assert any(d.doc_id == doc.doc_id for d in it_docs)
        assert not any(d.doc_id == doc.doc_id for d in fin_docs)

    async def test_global_auditor_sees_all_docs(self, session: AsyncSession):
        auditor_role = Role(
            role_name=f"global_aud_{uuid.uuid4().hex[:6]}",
            role_type=RoleType.GLOBAL_AUDITOR,
            domain=None,
        )
        it_role = Role(role_name=f"it2_{uuid.uuid4().hex[:6]}", role_type=RoleType.FUNCTIONAL, domain="IT")
        session.add_all([auditor_role, it_role])
        await session.flush()

        auditor = await user_service.create_user(session, f"aud_{uuid.uuid4().hex[:6]}@test.com", "pass")
        await user_service.assign_role(session, auditor.user_id, auditor_role.role_id)

        doc = await document_service.register_document(session, "IT Only Doc", "file:///itonly.pdf", None)
        await access_service.set_document_access(session, doc.doc_id, [it_role.role_id])

        auditor_docs = await access_service.get_accessible_docs(session, auditor.user_id)
        assert any(d.doc_id == doc.doc_id for d in auditor_docs)
