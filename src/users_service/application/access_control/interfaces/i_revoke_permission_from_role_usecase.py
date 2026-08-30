from abc import ABC, abstractmethod

from users_service.entities.permission.value_objects import PermissionId
from users_service.entities.role.models import Role
from users_service.entities.role.value_objects import RoleId


class IRevokePermissionFromRoleUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> Role: ...
