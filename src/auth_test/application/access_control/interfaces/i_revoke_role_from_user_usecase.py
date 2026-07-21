from abc import ABC, abstractmethod

from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import UserId


class IRevokeRoleFromUserUseCase(ABC):
    @abstractmethod
    async def __call__(self, user_id: UserId, role_id: RoleId) -> User: ...
