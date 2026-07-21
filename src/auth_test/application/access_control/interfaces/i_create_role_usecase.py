from abc import ABC, abstractmethod

from auth_test.entities.role.models import Role


class ICreateRoleUseCase(ABC):
    @abstractmethod
    async def __call__(self, name: str, description: str | None) -> Role: ...
