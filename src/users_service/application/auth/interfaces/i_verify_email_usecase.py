from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO
from users_service.entities.user.models import User


class IVerifyEmailUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, token: str, device: DeviceInfoDTO | None = None
    ) -> User: ...
