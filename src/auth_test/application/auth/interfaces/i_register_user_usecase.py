from abc import ABC, abstractmethod

from auth_test.application.common.dto import RegisterUserDTO
from auth_test.entities.user.models import User


class IRegisterUserUseCase(ABC):
    @abstractmethod
    async def __call__(self, data: RegisterUserDTO) -> User: ...
