from auth_test.application.access_control.interfaces.i_list_roles_usecase import (
    IListRolesUseCase,
)
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.role.models import Role


class ListRolesUseCase(IListRolesUseCase):
    """Read every role together with the permissions it grants."""

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self) -> list[Role]:
        async with self._uow as uow:
            return await uow.roles.list_all()
