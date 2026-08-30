from abc import ABC, abstractmethod

from users_service.entities.permission.models import Permission


class IListPermissionsUseCase(ABC):
    @abstractmethod
    async def __call__(self) -> list[Permission]: ...
