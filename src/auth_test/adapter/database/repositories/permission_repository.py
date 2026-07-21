from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_test.adapter.database.mappers.permission_mapper import (
    permission_to_entity,
)
from auth_test.adapter.database.orm_models.permission_orm import PermissionORM
from auth_test.application.common.interfaces.repositories.i_permission_repository import (
    IPermissionRepository,
)
from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId


class SqlAlchemyPermissionRepository(IPermissionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, resource: str, action: str, description: str | None
    ) -> Permission:
        row = PermissionORM(resource=resource, action=action, description=description)
        self._session.add(row)
        await self._session.flush()
        return permission_to_entity(row)

    async def get_by_id(self, permission_id: PermissionId) -> Permission | None:
        row = await self._session.get(PermissionORM, int(permission_id))
        return permission_to_entity(row) if row is not None else None

    async def get_by_resource_action(
        self, resource: str, action: str
    ) -> Permission | None:
        result = await self._session.execute(
            select(PermissionORM).where(
                PermissionORM.resource == resource,
                PermissionORM.action == action,
            )
        )
        row = result.scalar_one_or_none()
        return permission_to_entity(row) if row is not None else None

    async def list_all(self) -> list[Permission]:
        result = await self._session.execute(
            select(PermissionORM).order_by(PermissionORM.id)
        )
        return [permission_to_entity(row) for row in result.scalars().all()]

    async def delete(self, permission_id: PermissionId) -> None:
        await self._session.execute(
            delete(PermissionORM).where(PermissionORM.id == int(permission_id))
        )
        await self._session.flush()
