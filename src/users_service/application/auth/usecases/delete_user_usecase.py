from users_service.application.auth.interfaces.i_delete_user_usecase import (
    IDeleteUserUseCase,
)
from users_service.application.common import user_cache_codec
from users_service.application.common.errors import UserNotFoundError
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.entities.user.value_objects import UserId


class DeleteUserUseCase(IDeleteUserUseCase):
    """Soft-delete: deactivate the account and revoke its sessions.

    The row stays in the database with ``is_active=False``. Because
    :class:`LoginUseCase` and :class:`AuthenticateUseCase` both reject inactive
    users, the account can neither log in again nor keep using existing
    tokens — revoking every session forces an immediate logout. Both writes
    commit in one transaction so a user is never left half-deleted.
    """

    def __init__(self, uow: IUnitOfWork, cache: ICache) -> None:
        self._uow = uow
        self._cache = cache

    async def __call__(self, user_id: UserId) -> None:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError()

            user.is_active = False
            await uow.users.update(user)
            await uow.sessions.revoke_all_for_user(user_id)
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(user_id))
