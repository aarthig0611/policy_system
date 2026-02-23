"""Seed the database with one user per role type for local development/testing."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from backend.admin.user_service import assign_role, create_user, get_user_by_email
from backend.core.exceptions import ValidationError
from backend.db.models import Role, RoleType
from backend.db.session import get_session

SEED_ROLES = [
    {"role_name": "System Administrators", "role_type": RoleType.SYSTEM_ADMIN,  "domain": None},
    {"role_name": "Global Auditors",        "role_type": RoleType.GLOBAL_AUDITOR, "domain": None},
    {"role_name": "Engineering Auditors",   "role_type": RoleType.DOMAIN_AUDITOR, "domain": "Engineering"},
    {"role_name": "Engineering Users",      "role_type": RoleType.FUNCTIONAL,     "domain": "Engineering"},
]

SEED_USERS = [
    {"email": "admin@example.com",          "password": "Admin1234!", "role_name": "System Administrators"},
    {"email": "global.auditor@example.com", "password": "Admin1234!", "role_name": "Global Auditors"},
    {"email": "domain.auditor@example.com", "password": "Admin1234!", "role_name": "Engineering Auditors"},
    {"email": "user@example.com",           "password": "Admin1234!", "role_name": "Engineering Users"},
]


async def main() -> None:
    async with get_session() as session:
        # Upsert roles
        role_map: dict[str, Role] = {}
        for r in SEED_ROLES:
            result = await session.execute(select(Role).where(Role.role_name == r["role_name"]))
            role = result.scalar_one_or_none()
            if role is None:
                role = Role(**r)
                session.add(role)
                await session.flush()
                print(f"  Created role: {r['role_name']}")
            else:
                print(f"  Role exists:  {r['role_name']}")
            role_map[r["role_name"]] = role

        # Upsert users and assign roles
        for u in SEED_USERS:
            try:
                user = await create_user(session, u["email"], u["password"])
                await session.flush()
                print(f"  Created user: {u['email']}")
            except ValidationError:
                user = await get_user_by_email(session, u["email"])
                print(f"  User exists:  {u['email']}")

            role = role_map[u["role_name"]]
            await assign_role(session, user.user_id, role.role_id)

    print("\nSeed complete. Credentials:")
    for u in SEED_USERS:
        print(f"  {u['email']} / {u['password']}")


if __name__ == "__main__":
    asyncio.run(main())
