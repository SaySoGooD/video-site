from abc import ABC, abstractmethod

from users_service.entities.role.models import Role


class IListRolesUseCase(ABC):
    @abstractmethod
    async def __call__(self) -> list[Role]: ...
