from auth_test.adapter.memory.storage import InMemoryStorage
from auth_test.application.common.interfaces.repositories.i_permission_repository import (  # noqa: E501
    IPermissionRepository,
)
from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId


class InMemoryPermissionRepository(IPermissionRepository):
    def __init__(self, storage: InMemoryStorage) -> None:
        self._storage = storage

    async def add(
        self, resource: str, action: str, description: str | None
    ) -> Permission:
        permission_id = PermissionId(self._storage.next_id("permission"))
        permission = Permission(
            id=permission_id,
            resource=resource,
            action=action,
            description=description,
        )
        self._storage.permissions[permission_id] = permission
        return permission

    async def get_by_id(self, permission_id: PermissionId) -> Permission | None:
        return self._storage.permissions.get(permission_id)

    async def get_by_resource_action(
        self, resource: str, action: str
    ) -> Permission | None:
        for permission in self._storage.permissions.values():
            if permission.resource == resource and permission.action == action:
                return permission
        return None

    async def list_all(self) -> list[Permission]:
        return [
            self._storage.permissions[pid]
            for pid in sorted(self._storage.permissions)
        ]

    async def delete(self, permission_id: PermissionId) -> None:
        self._storage.permissions.pop(permission_id, None)
        self._storage.role_permissions = {
            (rid, pid)
            for (rid, pid) in self._storage.role_permissions
            if pid != int(permission_id)
        }
