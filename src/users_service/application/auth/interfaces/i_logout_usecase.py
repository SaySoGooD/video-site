from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO


class ILogoutUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, token: str, device: DeviceInfoDTO | None = None
    ) -> None: ...
