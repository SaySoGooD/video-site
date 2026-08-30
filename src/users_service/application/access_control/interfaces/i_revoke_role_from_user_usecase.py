from abc import ABC, abstractmethod

from users_service.entities.role.value_objects import RoleId
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class IRevokeRoleFromUserUseCase(ABC):
    @abstractmethod
    async def __call__(self, user_id: UserId, role_id: RoleId) -> User: ...
