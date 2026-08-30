from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO
from users_service.entities.user.value_objects import UserId


class IRevokeAllSessionsUseCase(ABC):
    @abstractmethod
    async def __call__(
        self,
        user_id: UserId,
        except_jti: str | None = None,
        device: DeviceInfoDTO | None = None,
    ) -> int: ...
