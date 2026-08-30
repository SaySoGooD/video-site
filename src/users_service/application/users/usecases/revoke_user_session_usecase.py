from datetime import UTC, datetime

from users_service.application.common import audit
from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.common.errors import SessionNotFoundError
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.users.interfaces.i_revoke_user_session_usecase import (
    IRevokeUserSessionUseCase,
)
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import UserId


class RevokeUserSessionUseCase(IRevokeUserSessionUseCase):
    """Kill one of the caller's own logins ("sign out that other device").

    A session belonging to somebody else is reported as **404** rather than
    403, so the endpoint cannot be used to probe which session ids exist.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(
        self,
        user_id: UserId,
        session_id: SessionId,
        device: DeviceInfoDTO | None = None,
    ) -> None:
        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)
            if session is None or int(session.user_id) != int(user_id):
                raise SessionNotFoundError()

            await uow.sessions.revoke(session.jti, datetime.now(UTC))
            await audit.record(
                uow,
                AuditAction.SESSION_REVOKED,
                user_id=user_id,
                device=device,
                scope="one",
                session_id=int(session_id),
            )
            await uow.commit()
