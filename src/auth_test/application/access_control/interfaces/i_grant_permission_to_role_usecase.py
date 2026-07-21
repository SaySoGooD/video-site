from abc import ABC, abstractmethod

from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId


class IGrantPermissionToRoleUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, role_id: RoleId, permission_id: PermissionId
    ) -> Role: ...
