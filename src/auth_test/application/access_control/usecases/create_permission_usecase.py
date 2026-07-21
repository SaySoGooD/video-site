from auth_test.application.access_control.interfaces.i_create_permission_usecase import (
    ICreatePermissionUseCase,
)
from auth_test.application.common.errors import ConflictError
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.permission.models import Permission


class CreatePermissionUseCase(ICreatePermissionUseCase):
    """Define a new (resource, action) rule that roles can later grant."""

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(
        self, resource: str, action: str, description: str | None
    ) -> Permission:
        async with self._uow as uow:
            existing = await uow.permissions.get_by_resource_action(resource, action)
            if existing is not None:
                raise ConflictError(f"Permission {resource}:{action} already exists")
            permission = await uow.permissions.add(resource, action, description)
            await uow.commit()
            return permission
