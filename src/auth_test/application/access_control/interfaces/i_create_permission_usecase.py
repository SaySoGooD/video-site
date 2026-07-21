from abc import ABC, abstractmethod

from auth_test.entities.permission.models import Permission


class ICreatePermissionUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, resource: str, action: str, description: str | None
    ) -> Permission: ...
