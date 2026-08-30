from abc import ABC, abstractmethod

from users_service.entities.permission.models import Permission
from users_service.entities.permission.value_objects import PermissionId


class IPermissionRepository(ABC):
    """Persistence port for permissions."""

    @abstractmethod
    async def add(
        self, resource: str, action: str, description: str | None
    ) -> Permission:
        ...

    @abstractmethod
    async def get_by_id(self, permission_id: PermissionId) -> Permission | None:
        ...

    @abstractmethod
    async def get_by_resource_action(
        self, resource: str, action: str
    ) -> Permission | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[Permission]:
        ...

    @abstractmethod
    async def delete(self, permission_id: PermissionId) -> None:
        ...
