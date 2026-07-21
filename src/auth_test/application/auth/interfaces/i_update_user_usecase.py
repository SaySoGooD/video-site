from abc import ABC, abstractmethod

from auth_test.application.common.dto import UpdateUserDTO
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import UserId


class IUpdateUserUseCase(ABC):
    @abstractmethod
    async def __call__(self, user_id: UserId, data: UpdateUserDTO) -> User: ...
