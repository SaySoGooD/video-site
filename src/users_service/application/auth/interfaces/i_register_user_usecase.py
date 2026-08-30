from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO, RegisterUserDTO
from users_service.entities.user.models import User


class IRegisterUserUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, data: RegisterUserDTO, device: DeviceInfoDTO | None = None
    ) -> User: ...
