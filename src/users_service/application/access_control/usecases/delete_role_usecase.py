from users_service.application.access_control.interfaces.i_delete_role_usecase import (
    IDeleteRoleUseCase,
)
from users_service.application.common.errors import RoleNotFoundError
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.entities.role.value_objects import RoleId


class DeleteRoleUseCase(IDeleteRoleUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, role_id: RoleId) -> None:
        async with self._uow as uow:
            if await uow.roles.get_by_id(role_id) is None:
                raise RoleNotFoundError()
            await uow.roles.delete(role_id)
            await uow.commit()
