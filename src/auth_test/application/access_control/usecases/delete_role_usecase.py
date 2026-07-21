from auth_test.application.access_control.interfaces.i_delete_role_usecase import (
    IDeleteRoleUseCase,
)
from auth_test.application.common.errors import RoleNotFoundError
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.role.value_objects import RoleId


class DeleteRoleUseCase(IDeleteRoleUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, role_id: RoleId) -> None:
        async with self._uow as uow:
            if await uow.roles.get_by_id(role_id) is None:
                raise RoleNotFoundError()
            await uow.roles.delete(role_id)
            await uow.commit()
