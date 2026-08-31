from users_service.application.common import audit, user_cache_codec
from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.common.errors import UserNotFoundError
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.moderation.interfaces.i_unban_user_usecase import (
    IUnbanUserUseCase,
)
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class UnbanUserUseCase(IUnbanUserUseCase):
    """Reactivate an account a moderator had banned.

    Reactivating does not restore the old sessions: they were revoked, and
    revocation is final. The user logs in again, which is the correct outcome
    anyway if the ban followed a compromise.
    """

    def __init__(self, uow: IUnitOfWork, cache: ICache) -> None:
        self._uow = uow
        self._cache = cache

    async def __call__(
        self,
        actor: User,
        target_id: UserId,
        device: DeviceInfoDTO | None = None,
    ) -> User:
        async with self._uow as uow:
            target = await uow.users.get_by_id(target_id)
            if target is None:
                raise UserNotFoundError()

            if target.is_active:
                return target

            target.is_active = True
            restored = await uow.users.update(target)
            await audit.record(
                uow,
                AuditAction.USER_UNBANNED,
                user_id=target_id,
                device=device,
                actor_id=int(actor.id),
            )
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(target_id))
        return restored
