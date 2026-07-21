from auth_test.application.access_control.interfaces.i_list_users_usecase import (
    IListUsersUseCase,
)
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.user.models import User


class ListUsersUseCase(IListUsersUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self) -> list[User]:
        async with self._uow as uow:
            return await uow.users.list_all()
