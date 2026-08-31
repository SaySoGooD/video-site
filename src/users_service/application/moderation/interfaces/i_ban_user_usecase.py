from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class IBanUserUseCase(ABC):
    @abstractmethod
    async def __call__(
        self,
        actor: User,
        target_id: UserId,
        reason: str | None = None,
        device: DeviceInfoDTO | None = None,
    ) -> User: ...
