from datetime import UTC, datetime

from users_service.application.common import audit
from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.users.interfaces.i_revoke_all_sessions_usecase import (
    IRevokeAllSessionsUseCase,
)
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.user.value_objects import UserId


class RevokeAllSessionsUseCase(IRevokeAllSessionsUseCase):
    """Sign the user out everywhere — optionally sparing the current device.

    Two readings of "log out from all devices" are both legitimate, so the
    caller picks: keeping the current session is the "something feels wrong,
    kick everyone else" button, dropping it too is a full sign-out. Returns
    how many sessions were killed so the UI can say so.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(
        self,
        user_id: UserId,
        except_jti: str | None = None,
        device: DeviceInfoDTO | None = None,
    ) -> int:
        async with self._uow as uow:
            revoked = await uow.sessions.revoke_all_for_user(
                user_id, datetime.now(UTC), except_jti=except_jti
            )
            await audit.record(
                uow,
                AuditAction.SESSION_REVOKED,
                user_id=user_id,
                device=device,
                scope="all" if except_jti is None else "others",
                sessions_revoked=revoked,
            )
            await uow.commit()
            return revoked
