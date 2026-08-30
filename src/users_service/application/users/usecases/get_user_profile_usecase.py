from users_service.application.common.errors import UserNotFoundError
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.users.interfaces.i_get_user_profile_usecase import (
    IGetUserProfileUseCase,
)
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class GetUserProfileUseCase(IGetUserProfileUseCase):
    """Look up one account by id.

    A soft-deleted (inactive) account is reported as **404**, not as an empty
    profile: to everyone but an administrator it no longer exists. The caller
    decides how much of the returned user to expose — the public serializer
    drops the email and every other private field.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, user_id: UserId) -> User:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None or not user.is_active:
                raise UserNotFoundError()
            return user
