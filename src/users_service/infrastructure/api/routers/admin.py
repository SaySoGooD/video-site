from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from users_service.application.access_control.interfaces.i_assign_role_to_user_usecase import (
    IAssignRoleToUserUseCase,
)
from users_service.application.access_control.interfaces.i_create_permission_usecase import (
    ICreatePermissionUseCase,
)
from users_service.application.access_control.interfaces.i_create_role_usecase import (
    ICreateRoleUseCase,
)
from users_service.application.access_control.interfaces.i_delete_role_usecase import (
    IDeleteRoleUseCase,
)
from users_service.application.access_control.interfaces.i_grant_permission_to_role_usecase import (
    IGrantPermissionToRoleUseCase,
)
from users_service.application.access_control.interfaces.i_list_permissions_usecase import (
    IListPermissionsUseCase,
)
from users_service.application.access_control.interfaces.i_list_roles_usecase import (
    IListRolesUseCase,
)
from users_service.application.access_control.interfaces.i_list_users_usecase import (
    IListUsersUseCase,
)
from users_service.application.access_control.interfaces.i_revoke_permission_from_role_usecase import (  # noqa: E501
    IRevokePermissionFromRoleUseCase,
)
from users_service.application.access_control.interfaces.i_revoke_role_from_user_usecase import (
    IRevokeRoleFromUserUseCase,
)
from users_service.dependency_injection import Container
from users_service.entities.permission.value_objects import PermissionId
from users_service.entities.role.value_objects import RoleId
from users_service.entities.user.value_objects import UserId
from users_service.infrastructure.api.dependencies import require_permission
from users_service.infrastructure.api.models.access_control import (
    CreatePermissionRequest,
    CreateRoleRequest,
    PermissionResponse,
    RolePermissionRequest,
    RoleResponse,
    UserRoleRequest,
)
from users_service.infrastructure.api.models.user_response import UserResponse
from users_service.infrastructure.api.serializers import to_user_response

router = APIRouter(
    prefix="/admin",
    tags=["access-control (admin)"],
    dependencies=[Depends(require_permission("access_control", "manage"))],
)


@router.get("/permissions", response_model=list[PermissionResponse])
@inject
async def list_permissions(
    usecase: IListPermissionsUseCase = Depends(
        Provide[Container.list_permissions_usecase]
    ),
) -> list[PermissionResponse]:
    """List every defined (resource, action) permission."""
    permissions = await usecase()
    return [PermissionResponse.model_validate(p) for p in permissions]


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def create_permission(
    body: CreatePermissionRequest,
    usecase: ICreatePermissionUseCase = Depends(
        Provide[Container.create_permission_usecase]
    ),
) -> PermissionResponse:
    """Define a new permission rule."""
    permission = await usecase(body.resource, body.action, body.description)
    return PermissionResponse.model_validate(permission)


@router.get("/roles", response_model=list[RoleResponse])
@inject
async def list_roles(
    usecase: IListRolesUseCase = Depends(Provide[Container.list_roles_usecase]),
) -> list[RoleResponse]:
    """List every role with the permissions it grants."""
    roles = await usecase()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post(
    "/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED
)
@inject
async def create_role(
    body: CreateRoleRequest,
    usecase: ICreateRoleUseCase = Depends(Provide[Container.create_role_usecase]),
) -> RoleResponse:
    """Create a new (empty) role."""
    role = await usecase(body.name, body.description)
    return RoleResponse.model_validate(role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_role(
    role_id: int,
    usecase: IDeleteRoleUseCase = Depends(Provide[Container.delete_role_usecase]),
) -> None:
    """Delete a role. 404 if it does not exist."""
    await usecase(RoleId(role_id))


@router.post("/roles/{role_id}/permissions", response_model=RoleResponse)
@inject
async def grant_permission_to_role(
    role_id: int,
    body: RolePermissionRequest,
    usecase: IGrantPermissionToRoleUseCase = Depends(
        Provide[Container.grant_permission_to_role_usecase]
    ),
) -> RoleResponse:
    """Attach a permission to a role."""
    role = await usecase(RoleId(role_id), PermissionId(body.permission_id))
    return RoleResponse.model_validate(role)


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    response_model=RoleResponse,
)
@inject
async def revoke_permission_from_role(
    role_id: int,
    permission_id: int,
    usecase: IRevokePermissionFromRoleUseCase = Depends(
        Provide[Container.revoke_permission_from_role_usecase]
    ),
) -> RoleResponse:
    """Detach a permission from a role."""
    role = await usecase(RoleId(role_id), PermissionId(permission_id))
    return RoleResponse.model_validate(role)


@router.get("/users", response_model=list[UserResponse])
@inject
async def list_users(
    usecase: IListUsersUseCase = Depends(Provide[Container.list_users_usecase]),
) -> list[UserResponse]:
    """List all users (active and soft-deleted) with their roles."""
    users = await usecase()
    return [to_user_response(u) for u in users]


@router.post("/users/{user_id}/roles", response_model=UserResponse)
@inject
async def assign_role_to_user(
    user_id: int,
    body: UserRoleRequest,
    usecase: IAssignRoleToUserUseCase = Depends(
        Provide[Container.assign_role_to_user_usecase]
    ),
) -> UserResponse:
    """Grant a role to a user."""
    user = await usecase(UserId(user_id), RoleId(body.role_id))
    return to_user_response(user)


@router.delete("/users/{user_id}/roles/{role_id}", response_model=UserResponse)
@inject
async def revoke_role_from_user(
    user_id: int,
    role_id: int,
    usecase: IRevokeRoleFromUserUseCase = Depends(
        Provide[Container.revoke_role_from_user_usecase]
    ),
) -> UserResponse:
    """Remove a role from a user."""
    user = await usecase(UserId(user_id), RoleId(role_id))
    return to_user_response(user)
