from abc import ABC, abstractmethod

from users_service.application.common.dto import DeviceInfoDTO
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import UserId


class IRevokeUserSessionUseCase(ABC):
    @abstractmethod
    async def __call__(
        self,
        user_id: UserId,
        session_id: SessionId,
        device: DeviceInfoDTO | None = None,
    ) -> None: ...
