from auth_test.application.access_control.interfaces.i_assign_role_to_user_usecase import (
    IAssignRoleToUserUseCase,
)
from auth_test.application.common import user_cache_codec
from auth_test.application.common.errors import (
    RoleNotFoundError,
    UserNotFoundError,
)
from auth_test.application.common.interfaces.i_cache import ICache
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import UserId


class AssignRoleToUserUseCase(IAssignRoleToUserUseCase):
    """Grant a role to a user — changes what that user is allowed to do.

    The user's cache entry is invalidated so the new role takes effect on the
    next request.
    """

    def __init__(self, uow: IUnitOfWork, cache: ICache) -> None:
        self._uow = uow
        self._cache = cache

    async def __call__(self, user_id: UserId, role_id: RoleId) -> User:
        async with self._uow as uow:
            if await uow.users.get_by_id(user_id) is None:
                raise UserNotFoundError()
            if await uow.roles.get_by_id(role_id) is None:
                raise RoleNotFoundError()

            await uow.users.assign_role(user_id, role_id)
            await uow.commit()
            user = await uow.users.get_by_id(user_id)
            assert user is not None

        await self._cache.delete(user_cache_codec.user_cache_key(user_id))
        return user
