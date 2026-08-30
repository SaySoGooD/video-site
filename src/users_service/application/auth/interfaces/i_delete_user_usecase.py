from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO
from users_service.entities.user.value_objects import UserId


class IDeleteUserUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, user_id: UserId, device: DeviceInfoDTO | None = None
    ) -> None: ...
