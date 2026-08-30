from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO


class IForgotPasswordUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, email: str, device: DeviceInfoDTO | None = None
    ) -> None: ...
