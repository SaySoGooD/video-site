from users_service.application.access_control.interfaces.i_list_permissions_usecase import (
    IListPermissionsUseCase,
)
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.entities.permission.models import Permission


class ListPermissionsUseCase(IListPermissionsUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self) -> list[Permission]:
        async with self._uow as uow:
            return await uow.permissions.list_all()
