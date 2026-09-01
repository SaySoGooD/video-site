from datetime import UTC, datetime

from users_service.application.auth.interfaces.i_change_password_usecase import (
    IChangePasswordUseCase,
)
from users_service.application.common import audit, user_cache_codec
from users_service.application.common.dto import ChangePasswordDTO, DeviceInfoDTO
from users_service.application.common.errors import (
    InvalidCredentialsError,
    PasswordMismatchError,
    UserNotFoundError,
    ValidationError,
)
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.security_token.value_objects import TokenPurpose
from users_service.entities.user.value_objects import UserId


class ChangePasswordUseCase(IChangePasswordUseCase):
    """Change the password of a logged-in account and sign every device out.

    The current password is required even though the caller already holds a
    valid session. A session can be stolen; without this check, a stolen one
    could be turned into permanent ownership of the account by changing the
    password, and the real owner would be the one locked out.

    Every session is revoked, the caller's included, so the change behaves the
    same way whether the reason was hygiene or a suspected compromise: the old
    access token stops working on the next request, the old refresh token
    cannot mint a new one, and the browser is left with cookies that no longer
    authenticate anything. The user logs in again with the new password.

    Any outstanding reset link is spent as well — a "forgot password" email
    sitting in an inbox must not survive the password it was meant to replace.

    Returns how many sessions were revoked, so the API can tell the user how
    many devices were signed out.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        cache: ICache,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._cache = cache

    async def __call__(
        self,
        user_id: UserId,
        data: ChangePasswordDTO,
        device: DeviceInfoDTO | None = None,
    ) -> int:
        if data.new_password != data.new_password_repeat:
            raise PasswordMismatchError()

        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError()

            if not self._hasher.verify(data.current_password, user.password_hash):
                raise InvalidCredentialsError("Current password is incorrect")

            if data.current_password == data.new_password:
                raise ValidationError(
                    "The new password must differ from the current one"
                )

            user.password_hash = self._hasher.hash(data.new_password)
            await uow.users.update_password(user)

            await uow.security_tokens.invalidate_for_user(
                user_id, TokenPurpose.PASSWORD_RESET
            )
            revoked = await uow.sessions.revoke_all_for_user(
                user_id, datetime.now(UTC)
            )

            await audit.record(
                uow,
                AuditAction.PASSWORD_CHANGED,
                user_id=user_id,
                device=device,
                sessions_revoked=revoked,
            )
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(user_id))
        return revoked
