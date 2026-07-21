from abc import ABC, abstractmethod

from auth_test.entities.user.value_objects import UserId


class IDeleteUserUseCase(ABC):
    @abstractmethod
    async def __call__(self, user_id: UserId) -> None: ...
