from abc import ABC, abstractmethod

from users_service.application.common.dto import AuthResultDTO, DeviceInfoDTO


class IRefreshTokenUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, refresh_token: str, device: DeviceInfoDTO | None = None
    ) -> AuthResultDTO: ...
