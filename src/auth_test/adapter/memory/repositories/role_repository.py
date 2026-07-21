from auth_test.adapter.memory.storage import InMemoryStorage
from auth_test.application.common.interfaces.repositories.i_role_repository import (
    IRoleRepository,
)
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId


class InMemoryRoleRepository(IRoleRepository):
    def __init__(self, storage: InMemoryStorage) -> None:
        self._storage = storage

    async def add(self, name: str, description: str | None) -> Role:
        role_id = RoleId(self._storage.next_id("role"))
        self._storage.roles[role_id] = Role(
            id=role_id, name=name, description=description, permissions=[]
        )
        return self._storage.build_role(role_id)

    async def get_by_id(self, role_id: RoleId) -> Role | None:
        if role_id not in self._storage.roles:
            return None
        return self._storage.build_role(role_id)

    async def get_by_name(self, name: str) -> Role | None:
        for role_id, role in self._storage.roles.items():
            if role.name == name:
                return self._storage.build_role(role_id)
        return None

    async def list_all(self) -> list[Role]:
        return [self._storage.build_role(rid) for rid in sorted(self._storage.roles)]

    async def delete(self, role_id: RoleId) -> None:
        self._storage.roles.pop(role_id, None)
        self._storage.role_permissions = {
            (rid, pid)
            for (rid, pid) in self._storage.role_permissions
            if rid != int(role_id)
        }
        self._storage.user_roles = {
            (uid, rid)
            for (uid, rid) in self._storage.user_roles
            if rid != int(role_id)
        }

    async def grant_permission(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> None:
        self._storage.role_permissions.add((int(role_id), int(permission_id)))

    async def revoke_permission(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> None:
        self._storage.role_permissions.discard((int(role_id), int(permission_id)))
