"""Create the PostgreSQL schema and load demo data for a runnable demo.

This is a convenience seeder, not a migration tool — in a real deployment the
schema would be managed by Alembic. It is idempotent: it does nothing if users
already exist, so restarts do not duplicate rows. Demo data lives in
``adapter/seed_data.py``.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from users_service.adapter.database.base import Base
from users_service.adapter.database.orm_models.permission_orm import PermissionORM
from users_service.adapter.database.orm_models.role_orm import RoleORM
from users_service.adapter.database.orm_models.user_orm import UserORM
from users_service.adapter.seed_data import (
    PERMISSIONS,
    ROLE_DESCRIPTIONS,
    ROLE_GRANTS,
    USERS,
)
from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)


async def create_schema(engine: AsyncEngine) -> None:
    """Create all tables if they do not yet exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_demo_data(engine: AsyncEngine, hasher: IPasswordHasher) -> None:
    """Populate demo permissions/roles/users unless data already exists."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        existing = await session.execute(select(UserORM.id).limit(1))
        if existing.first() is not None:
            return

        permissions: dict[tuple[str, str], PermissionORM] = {}
        for resource, action, description in PERMISSIONS:
            perm = PermissionORM(
                resource=resource, action=action, description=description
            )
            session.add(perm)
            permissions[(resource, action)] = perm

        roles: dict[str, RoleORM] = {}
        for name, grants in ROLE_GRANTS.items():
            role = RoleORM(name=name, description=ROLE_DESCRIPTIONS[name])
            role.permissions = [permissions[key] for key in grants]
            session.add(role)
            roles[name] = role

        now = datetime.now(UTC)
        for email, username, password, display, is_super, role_name in USERS:
            user = UserORM(
                email=email,
                username=username,
                password_hash=hasher.hash(password),
                display_name=display,
                is_active=True,
                is_superuser=is_super,
                created_at=now,
                updated_at=now,
            )
            user.roles = [roles[role_name]]
            session.add(user)

        await session.commit()
