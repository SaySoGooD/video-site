from abc import ABC, abstractmethod

from users_service.entities.user.models import User


class IListUsersUseCase(ABC):
    @abstractmethod
    async def __call__(self) -> list[User]: ...
