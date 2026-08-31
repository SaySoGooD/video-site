from datetime import UTC, datetime

from users_service.application.common import audit, user_cache_codec
from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.common.errors import (
    AuthorizationError,
    UserNotFoundError,
    ValidationError,
)
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.moderation.interfaces.i_ban_user_usecase import (
    IBanUserUseCase,
)
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class BanUserUseCase(IBanUserUseCase):
    """Deactivate somebody else's account and sign it out everywhere.

    A ban is the same state as a self-deactivation — ``is_active=False`` —
    because from the login path they mean the same thing: this account cannot
    authenticate. What separates them is the audit row, which records who did
    it and why.

    Two guards, both about the moderator rather than the target. A moderator
    cannot ban themselves, which would lock them out mid-action for no good
    reason; and cannot ban a superuser, or the ``users.ban`` permission would
    quietly become a way to decapitate the administrators.

    Deactivating and revoking the sessions commit together: a banned account
    whose refresh token still worked would be banned in name only.
    """

    def __init__(self, uow: IUnitOfWork, cache: ICache) -> None:
        self._uow = uow
        self._cache = cache

    async def __call__(
        self,
        actor: User,
        target_id: UserId,
        reason: str | None = None,
        device: DeviceInfoDTO | None = None,
    ) -> User:
        if int(actor.id) == int(target_id):
            raise ValidationError("You cannot ban your own account")

        async with self._uow as uow:
            target = await uow.users.get_by_id(target_id)
            if target is None:
                raise UserNotFoundError()

            if target.is_superuser:
                raise AuthorizationError("Superusers cannot be banned")

            if not target.is_active:
                # Already inactive: nothing to change, and no second audit row
                # claiming a ban that did not happen.
                return target

            target.is_active = False
            banned = await uow.users.update(target)
            revoked = await uow.sessions.revoke_all_for_user(
                target_id, datetime.now(UTC)
            )
            await audit.record(
                uow,
                AuditAction.USER_BANNED,
                user_id=target_id,
                device=device,
                actor_id=int(actor.id),
                reason=reason,
                sessions_revoked=revoked,
            )
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(target_id))
        return banned
