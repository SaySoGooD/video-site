from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.users.interfaces.i_list_user_sessions_usecase import (
    IListUserSessionsUseCase,
)
from users_service.entities.session.models import AuthSession
from users_service.entities.user.value_objects import UserId


class ListUserSessionsUseCase(IListUserSessionsUseCase):
    """List the caller's own live logins, one row per device."""

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, user_id: UserId) -> list[AuthSession]:
        async with self._uow as uow:
            return await uow.sessions.list_active_for_user(user_id)
