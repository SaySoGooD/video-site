from auth_test.application.access_control.interfaces.i_list_permissions_usecase import (
    IListPermissionsUseCase,
)
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.permission.models import Permission


class ListPermissionsUseCase(IListPermissionsUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self) -> list[Permission]:
        async with self._uow as uow:
            return await uow.permissions.list_all()
