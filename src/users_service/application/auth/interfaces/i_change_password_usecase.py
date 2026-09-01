from abc import ABC, abstractmethod

from users_service.application.common.dto import ChangePasswordDTO, DeviceInfoDTO
from users_service.entities.user.value_objects import UserId


class IChangePasswordUseCase(ABC):
    @abstractmethod
    async def __call__(
        self,
        user_id: UserId,
        data: ChangePasswordDTO,
        device: DeviceInfoDTO | None = None,
    ) -> int: ...
