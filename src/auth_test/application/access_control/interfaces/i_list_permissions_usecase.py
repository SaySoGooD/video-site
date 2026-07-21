from abc import ABC, abstractmethod

from auth_test.entities.permission.models import Permission


class IListPermissionsUseCase(ABC):
    @abstractmethod
    async def __call__(self) -> list[Permission]: ...
