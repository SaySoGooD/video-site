from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from users_service.adapter.database.base import role_permissions
from users_service.adapter.database.mappers.role_mapper import role_to_entity
from users_service.adapter.database.orm_models.role_orm import RoleORM
from users_service.application.common.interfaces.repositories.i_role_repository import (
    IRoleRepository,
)
from users_service.entities.permission.value_objects import PermissionId
from users_service.entities.role.models import Role
from users_service.entities.role.value_objects import RoleId


class SqlAlchemyRoleRepository(IRoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, name: str, description: str | None) -> Role:
        row = RoleORM(name=name, description=description)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row, attribute_names=["permissions"])
        return role_to_entity(row)

    async def get_by_id(self, role_id: RoleId) -> Role | None:
        row = await self._session.get(RoleORM, int(role_id))
        return role_to_entity(row) if row is not None else None

    async def get_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(
            select(RoleORM).where(RoleORM.name == name)
        )
        row = result.scalar_one_or_none()
        return role_to_entity(row) if row is not None else None

    async def list_all(self) -> list[Role]:
        result = await self._session.execute(select(RoleORM).order_by(RoleORM.id))
        return [role_to_entity(row) for row in result.scalars().all()]

    async def delete(self, role_id: RoleId) -> None:
        await self._session.execute(delete(RoleORM).where(RoleORM.id == int(role_id)))
        await self._session.flush()

    async def grant_permission(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> None:
        exists = await self._session.execute(
            select(role_permissions).where(
                role_permissions.c.role_id == int(role_id),
                role_permissions.c.permission_id == int(permission_id),
            )
        )
        if exists.first() is not None:
            return
        await self._session.execute(
            insert(role_permissions).values(
                role_id=int(role_id), permission_id=int(permission_id)
            )
        )
        await self._session.flush()

    async def revoke_permission(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> None:
        await self._session.execute(
            delete(role_permissions).where(
                role_permissions.c.role_id == int(role_id),
                role_permissions.c.permission_id == int(permission_id),
            )
        )
        await self._session.flush()
