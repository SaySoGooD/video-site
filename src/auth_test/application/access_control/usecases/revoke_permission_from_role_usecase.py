from auth_test.application.access_control.interfaces.i_revoke_permission_from_role_usecase import (
    IRevokePermissionFromRoleUseCase,
)
from auth_test.application.common.errors import RoleNotFoundError
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId


class RevokePermissionFromRoleUseCase(IRevokePermissionFromRoleUseCase):
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, role_id: RoleId, permission_id: PermissionId) -> Role:
        async with self._uow as uow:
            if await uow.roles.get_by_id(role_id) is None:
                raise RoleNotFoundError()

            await uow.roles.revoke_permission(role_id, permission_id)
            await uow.commit()
            role = await uow.roles.get_by_id(role_id)
            assert role is not None
            return role
