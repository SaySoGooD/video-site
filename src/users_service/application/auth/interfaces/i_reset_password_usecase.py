from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO, ResetPasswordDTO


class IResetPasswordUseCase(ABC):
    @abstractmethod
    async def __call__(
        self, data: ResetPasswordDTO, device: DeviceInfoDTO | None = None
    ) -> None: ...
