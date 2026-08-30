from abc import ABC, abstractmethod

from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class IGetUserProfileUseCase(ABC):
    @abstractmethod
    async def __call__(self, user_id: UserId) -> User: ...
