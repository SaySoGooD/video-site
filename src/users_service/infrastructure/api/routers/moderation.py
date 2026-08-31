"""Moderator actions on other people's accounts.

Separate from the ``/admin`` access-control router because it answers to a
different permission: ``users.ban`` rather than ``users.manage``. A moderator
should be able to stop an abusive account without also being able to hand
themselves the admin role.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends

from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.moderation.interfaces.i_ban_user_usecase import (
    IBanUserUseCase,
)
from users_service.application.moderation.interfaces.i_unban_user_usecase import (
    IUnbanUserUseCase,
)
from users_service.dependency_injection import Container
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId
from users_service.infrastructure.api.dependencies import (
    get_device_info,
    require_permission,
)
from users_service.infrastructure.api.models.moderation import BanUserRequest
from users_service.infrastructure.api.models.user_response import UserResponse
from users_service.infrastructure.api.serializers import to_user_response

router = APIRouter(prefix="/admin/users", tags=["moderation"])


@router.post("/{user_id}/ban", response_model=UserResponse)
@inject
async def ban_user(
    user_id: int,
    body: BanUserRequest = Body(default_factory=BanUserRequest),
    actor: User = Depends(require_permission("users", "ban")),
    device: DeviceInfoDTO = Depends(get_device_info),
    usecase: IBanUserUseCase = Depends(Provide[Container.ban_user_usecase]),
) -> UserResponse:
    """Deactivate an account and revoke every one of its sessions.

    404 if there is no such user, 403 if the target is a superuser, 422 if a
    moderator aims at their own account. Banning an already inactive account
    is a no-op rather than an error.
    """
    banned = await usecase(actor, UserId(user_id), body.reason, device)
    return to_user_response(banned)


@router.delete("/{user_id}/ban", response_model=UserResponse)
@inject
async def unban_user(
    user_id: int,
    actor: User = Depends(require_permission("users", "ban")),
    device: DeviceInfoDTO = Depends(get_device_info),
    usecase: IUnbanUserUseCase = Depends(Provide[Container.unban_user_usecase]),
) -> UserResponse:
    """Reactivate a banned account. The old sessions stay revoked."""
    restored = await usecase(actor, UserId(user_id), device)
    return to_user_response(restored)
