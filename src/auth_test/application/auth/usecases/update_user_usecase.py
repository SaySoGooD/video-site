from auth_test.application.auth.interfaces.i_update_user_usecase import (
    IUpdateUserUseCase,
)
from auth_test.application.common import user_cache_codec
from auth_test.application.common.dto import UpdateUserDTO
from auth_test.application.common.errors import (
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from auth_test.application.common.interfaces.i_cache import ICache
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import Email, UserId


class UpdateUserUseCase(IUpdateUserUseCase):
    """Edit a user's own profile fields.

    Only the provided (non-``None``) fields change. Changing the email is
    guarded against collisions with another account. The user's cache entry is
    invalidated so the change is visible on the next request.
    """

    def __init__(self, uow: IUnitOfWork, cache: ICache) -> None:
        self._uow = uow
        self._cache = cache

    async def __call__(self, user_id: UserId, data: UpdateUserDTO) -> User:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError()

            if data.email is not None and data.email != user.email:
                clash = await uow.users.get_by_email(data.email)
                if clash is not None:
                    raise EmailAlreadyExistsError()
                user.email = Email(data.email)

            if data.first_name is not None:
                user.first_name = data.first_name
            if data.last_name is not None:
                user.last_name = data.last_name
            if data.middle_name is not None:
                user.middle_name = data.middle_name

            updated = await uow.users.update(user)
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(user_id))
        return updated
