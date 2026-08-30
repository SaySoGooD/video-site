from abc import ABC, abstractmethod

from users_service.entities.permission.value_objects import PermissionId
from users_service.entities.role.models import Role
from users_service.entities.role.value_objects import RoleId


class IRoleRepository(ABC):
    """Persistence port for roles and their permission grants."""

    @abstractmethod
    async def add(self, name: str, description: str | None) -> Role:
        ...

    @abstractmethod
    async def get_by_id(self, role_id: RoleId) -> Role | None:
        ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Role | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[Role]:
        ...

    @abstractmethod
    async def delete(self, role_id: RoleId) -> None:
        ...

    @abstractmethod
    async def grant_permission(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> None:
        """Attach a permission to a role (idempotent)."""
        ...

    @abstractmethod
    async def revoke_permission(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> None:
        """Detach a permission from a role (idempotent)."""
        ...
