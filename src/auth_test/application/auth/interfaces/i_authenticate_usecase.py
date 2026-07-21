from abc import ABC, abstractmethod

from auth_test.entities.user.models import User


class IAuthenticateUseCase(ABC):
    @abstractmethod
    async def __call__(self, token: str) -> User: ...
