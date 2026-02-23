"""Integration tests for the FastAPI endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_handler import create_token
from backend.db.models import ResponseFormat, Role, RoleType, User, UserRole
from backend.auth.password import hash_password


def auth_headers(user: User) -> dict:
    token = create_token(str(user.user_id), user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_login_success(self, client: AsyncClient, session: AsyncSession):
        user = User(
            email=f"login_{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("testpassword"),
            default_format=ResponseFormat.EXECUTIVE_SUMMARY,
        )
        session.add(user)
        await session.flush()

        response = await client.post(
            "/auth/login",
            json={"email": user.email, "password": "testpassword"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, session: AsyncSession):
        user = User(
            email=f"badlogin_{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("realpassword"),
            default_format=ResponseFormat.EXECUTIVE_SUMMARY,
        )
        session.add(user)
        await session.flush()

        response = await client.post(
            "/auth/login",
            json={"email": user.email, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_get_me(self, client: AsyncClient, regular_user: User):
        response = await client.get("/auth/me", headers=auth_headers(regular_user))
        assert response.status_code == 200
        assert response.json()["email"] == regular_user.email

    async def test_get_me_no_token(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
class TestAdminEndpoints:
    async def test_create_user_as_admin(self, client: AsyncClient, admin_user: User):
        response = await client.post(
            "/admin/users",
            headers=auth_headers(admin_user),
            json={
                "email": f"newuser_{uuid.uuid4().hex[:8]}@test.com",
                "password": "newpassword",
                "default_format": "EXECUTIVE_SUMMARY",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data

    async def test_create_user_as_regular_user_forbidden(
        self, client: AsyncClient, regular_user: User
    ):
        response = await client.post(
            "/admin/users",
            headers=auth_headers(regular_user),
            json={
                "email": f"blocked_{uuid.uuid4().hex[:8]}@test.com",
                "password": "password123",
            },
        )
        assert response.status_code == 403

    async def test_register_document(self, client: AsyncClient, admin_user: User, session: AsyncSession):
        # Create a role for document access
        role = Role(
            role_name=f"doc_role_{uuid.uuid4().hex[:6]}",
            role_type=RoleType.FUNCTIONAL,
            domain="IT",
        )
        session.add(role)
        await session.flush()

        response = await client.post(
            "/admin/documents",
            headers=auth_headers(admin_user),
            json={
                "title": "Test Policy Document",
                "storage_uri": "file:///test.pdf",
                "role_ids": [str(role.role_id)],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Policy Document"
        assert len(data["roles"]) == 1

    async def test_list_users(self, client: AsyncClient, admin_user: User):
        response = await client.get("/admin/users", headers=auth_headers(admin_user))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_archive_toggle(self, client: AsyncClient, admin_user: User, session: AsyncSession):
        role = Role(
            role_name=f"arch_role_{uuid.uuid4().hex[:6]}",
            role_type=RoleType.FUNCTIONAL,
            domain="IT",
        )
        session.add(role)
        await session.flush()

        create_resp = await client.post(
            "/admin/documents",
            headers=auth_headers(admin_user),
            json={
                "title": "Archive Test Doc",
                "storage_uri": "file:///archive.pdf",
                "role_ids": [str(role.role_id)],
            },
        )
        doc_id = create_resp.json()["doc_id"]

        archive_resp = await client.patch(
            f"/admin/documents/{doc_id}/archive",
            headers=auth_headers(admin_user),
            json={"is_archived": True},
        )
        assert archive_resp.status_code == 200
        assert archive_resp.json()["is_archived"] is True
