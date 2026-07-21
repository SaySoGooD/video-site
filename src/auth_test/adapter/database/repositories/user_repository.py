from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_test.adapter.database.base import user_roles
from auth_test.adapter.database.mappers.user_mapper import user_to_entity
from auth_test.adapter.database.orm_models.user_orm import UserORM
from auth_test.application.common.interfaces.repositories.i_user_repository import (
    IUserRepository,
)
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import UserId


class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        row = UserORM(
            email=user.email,
            password_hash=user.password_hash,
            first_name=user.first_name,
            last_name=user.last_name,
            middle_name=user.middle_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(
            row, attribute_names=["created_at", "updated_at", "roles"]
        )
        return user_to_entity(row)

    async def get_by_id(self, user_id: UserId) -> User | None:
        row = await self._session.get(UserORM, int(user_id))
        return user_to_entity(row) if row is not None else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserORM).where(UserORM.email == email)
        )
        row = result.scalar_one_or_none()
        return user_to_entity(row) if row is not None else None

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserORM).order_by(UserORM.id))
        return [user_to_entity(row) for row in result.scalars().all()]

    async def update(self, user: User) -> User:
        row = await self._session.get(UserORM, int(user.id))
        if row is None:
            raise ValueError(f"User {user.id} disappeared during update")
        row.email = user.email
        row.first_name = user.first_name
        row.last_name = user.last_name
        row.middle_name = user.middle_name
        row.is_active = user.is_active
        row.is_superuser = user.is_superuser
        await self._session.flush()
        await self._session.refresh(
            row, attribute_names=["created_at", "updated_at", "roles"]
        )
        return user_to_entity(row)

    async def assign_role(self, user_id: UserId, role_id: RoleId) -> None:
        exists = await self._session.execute(
            select(user_roles).where(
                user_roles.c.user_id == int(user_id),
                user_roles.c.role_id == int(role_id),
            )
        )
        if exists.first() is not None:
            return
        await self._session.execute(
            insert(user_roles).values(user_id=int(user_id), role_id=int(role_id))
        )
        await self._session.flush()

    async def revoke_role(self, user_id: UserId, role_id: RoleId) -> None:
        await self._session.execute(
            delete(user_roles).where(
                user_roles.c.user_id == int(user_id),
                user_roles.c.role_id == int(role_id),
            )
        )
        await self._session.flush()
