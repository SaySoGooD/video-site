from abc import ABC, abstractmethod

from auth_test.entities.user.models import User


class IListUsersUseCase(ABC):
    @abstractmethod
    async def __call__(self) -> list[User]: ...
