from auth_test.application.access_control.interfaces.i_grant_permission_to_role_usecase import (
    IGrantPermissionToRoleUseCase,
)
from auth_test.application.common.errors import (
    PermissionNotFoundError,
    RoleNotFoundError,
)
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId


class GrantPermissionToRoleUseCase(IGrantPermissionToRoleUseCase):
    """Attach a permission to a role — the core "change the rules" operation."""

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, role_id: RoleId, permission_id: PermissionId) -> Role:
        async with self._uow as uow:
            if await uow.roles.get_by_id(role_id) is None:
                raise RoleNotFoundError()
            if await uow.permissions.get_by_id(permission_id) is None:
                raise PermissionNotFoundError()

            await uow.roles.grant_permission(role_id, permission_id)
            await uow.commit()
            role = await uow.roles.get_by_id(role_id)
            assert role is not None
            return role
