from users_service.application.access_control.interfaces.i_create_role_usecase import (
    ICreateRoleUseCase,
)
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.entities.role.models import Role


class CreateRoleUseCase(ICreateRoleUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, name: str, description: str | None) -> Role:
        async with self._uow as uow:
            role = await uow.roles.add(name, description)
            await uow.commit()
            return role
