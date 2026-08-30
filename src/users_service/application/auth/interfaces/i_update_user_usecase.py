from abc import ABC, abstractmethod

from users_service.application.common.dto import UpdateUserDTO
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class IUpdateUserUseCase(ABC):
    @abstractmethod
    async def __call__(self, user_id: UserId, data: UpdateUserDTO) -> User: ...
