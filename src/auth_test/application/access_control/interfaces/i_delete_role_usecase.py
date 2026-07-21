from abc import ABC, abstractmethod

from auth_test.entities.role.value_objects import RoleId


class IDeleteRoleUseCase(ABC):
    @abstractmethod
    async def __call__(self, role_id: RoleId) -> None: ...
