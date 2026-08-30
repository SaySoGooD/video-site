from abc import ABC, abstractmethod

from users_service.application.common.dto import (
    AuthResultDTO,
    DeviceInfoDTO,
    LoginDTO,
)


class ILoginUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, data: LoginDTO, device: DeviceInfoDTO | None = None
    ) -> AuthResultDTO: ...
