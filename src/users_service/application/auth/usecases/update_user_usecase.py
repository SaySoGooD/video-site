from users_service.application.auth.interfaces.i_update_user_usecase import (
    IUpdateUserUseCase,
)
from users_service.application.common import user_cache_codec
from users_service.application.common.dto import UpdateUserDTO
from users_service.application.common.errors import (
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import Email, UserId, Username


class UpdateUserUseCase(IUpdateUserUseCase):
    """Edit a user's own profile fields.

    Only the provided (non-``None``) fields change. Changing the email or the
    username is guarded against collisions with another account. The user's
    cache entry is invalidated so the change is visible on the next request.
    """

    def __init__(self, uow: IUnitOfWork, cache: ICache) -> None:
        self._uow = uow
        self._cache = cache

    async def __call__(self, user_id: UserId, data: UpdateUserDTO) -> User:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError()

            if data.email is not None:
                email = data.email.strip().lower()
                if email != user.email:
                    clash = await uow.users.get_by_email(email)
                    if clash is not None:
                        raise EmailAlreadyExistsError()
                    user.email = Email(email)

            if data.username is not None:
                username = data.username.strip()
                if username != user.username:
                    clash = await uow.users.get_by_username(username)
                    if clash is not None:
                        raise UsernameAlreadyExistsError()
                    user.username = Username(username)

            if data.display_name is not None:
                user.display_name = data.display_name

            updated = await uow.users.update(user)
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(user_id))
        return updated
