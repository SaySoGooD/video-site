from users_service.application.access_control.interfaces.i_list_users_usecase import (
    IListUsersUseCase,
)
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.entities.user.models import User


class ListUsersUseCase(IListUsersUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self) -> list[User]:
        async with self._uow as uow:
            return await uow.users.list_all()
