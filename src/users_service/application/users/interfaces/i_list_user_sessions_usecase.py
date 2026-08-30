from abc import ABC, abstractmethod

from users_service.entities.session.models import AuthSession
from users_service.entities.user.value_objects import UserId


class IListUserSessionsUseCase(ABC):
    @abstractmethod
    async def __call__(self, user_id: UserId) -> list[AuthSession]: ...
