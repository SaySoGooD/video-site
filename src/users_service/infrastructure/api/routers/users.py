"""Account endpoints that are *about* users rather than about logging in.

``/auth/*`` is the credential flow; ``/users/*`` is the profile and device
surface an account page is built from.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Response, status

from users_service.application.auth.interfaces.i_change_password_usecase import (
    IChangePasswordUseCase,
)
from users_service.application.auth.interfaces.i_delete_user_usecase import (
    IDeleteUserUseCase,
)
from users_service.application.auth.interfaces.i_update_user_usecase import (
    IUpdateUserUseCase,
)
from users_service.application.common.dto import (
    ChangePasswordDTO,
    DeviceInfoDTO,
    UpdateUserDTO,
)
from users_service.application.users.interfaces.i_get_user_profile_usecase import (
    IGetUserProfileUseCase,
)
from users_service.application.users.interfaces.i_list_user_sessions_usecase import (
    IListUserSessionsUseCase,
)
from users_service.application.users.interfaces.i_revoke_all_sessions_usecase import (
    IRevokeAllSessionsUseCase,
)
from users_service.application.users.interfaces.i_revoke_user_session_usecase import (
    IRevokeUserSessionUseCase,
)
from users_service.dependency_injection import Container
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId
from users_service.infrastructure.api.cookies import SessionCookies
from users_service.infrastructure.api.dependencies import (
    get_cookies,
    get_current_jti,
    get_current_user,
    get_device_info,
)
from users_service.infrastructure.api.models.auth import (
    ChangePasswordRequest,
    UpdateProfileRequest,
)
from users_service.infrastructure.api.models.public_user_response import (
    PublicUserResponse,
)
from users_service.infrastructure.api.models.session_response import (
    PasswordChangedResponse,
    RevokedSessionsResponse,
    SessionSummary,
)
from users_service.infrastructure.api.models.user_response import UserResponse
from users_service.infrastructure.api.serializers import (
    to_public_user_response,
    to_session_summary,
    to_user_response,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_me(user: User = Depends(get_current_user)) -> UserResponse:
    """The caller's own account, with roles, permissions and email state."""
    return to_user_response(user)


@router.patch("/me", response_model=UserResponse)
@inject
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    usecase: IUpdateUserUseCase = Depends(Provide[Container.update_user_usecase]),
) -> UserResponse:
    """Edit the caller's profile.

    Changing the email clears the verified flag and sends a confirmation link
    to the new address, so an account cannot be quietly pointed at an inbox
    somebody else controls.
    """
    updated = await usecase(
        user.id,
        UpdateUserDTO(
            username=body.username,
            display_name=body.display_name,
            email=str(body.email) if body.email is not None else None,
        ),
    )
    return to_user_response(updated)


@router.post("/me/password", response_model=PasswordChangedResponse)
@inject
async def change_my_password(
    body: ChangePasswordRequest,
    response: Response,
    user: User = Depends(get_current_user),
    device: DeviceInfoDTO = Depends(get_device_info),
    cookies: SessionCookies = Depends(get_cookies),
    usecase: IChangePasswordUseCase = Depends(
        Provide[Container.change_password_usecase]
    ),
) -> PasswordChangedResponse:
    """Change the password and sign every device out, this one included.

    Requires the current password: a stolen session must not be enough to take
    the account over. 401 if it is wrong, 422 if the new one does not match its
    repeat or equals the old one.

    Afterwards nothing that was issued before still authenticates — the old
    access token is refused, the old refresh token cannot rotate, and the
    browser cookies are cleared here. The user signs in again with the new
    password.
    """
    revoked = await usecase(
        user.id,
        ChangePasswordDTO(
            current_password=body.current_password,
            new_password=body.new_password,
            new_password_repeat=body.new_password_repeat,
        ),
        device,
    )
    cookies.clear_tokens(response)
    return PasswordChangedResponse(
        detail="Password updated. All sessions have been signed out.",
        sessions_revoked=revoked,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_me(
    response: Response,
    user: User = Depends(get_current_user),
    device: DeviceInfoDTO = Depends(get_device_info),
    cookies: SessionCookies = Depends(get_cookies),
    usecase: IDeleteUserUseCase = Depends(Provide[Container.delete_user_usecase]),
) -> None:
    """Soft-delete the account: deactivate it, revoke every session (204).

    The row stays — an account that uploaded content cannot simply vanish from
    under it — but nothing can log in as it again.
    """
    await usecase(user.id, device)
    cookies.clear_tokens(response)


@router.get("/me/sessions", response_model=list[SessionSummary])
@inject
async def list_my_sessions(
    user: User = Depends(get_current_user),
    current_jti: str = Depends(get_current_jti),
    usecase: IListUserSessionsUseCase = Depends(
        Provide[Container.list_user_sessions_usecase]
    ),
) -> list[SessionSummary]:
    """List the caller's live logins, newest first."""
    sessions = await usecase(user.id)
    return [to_session_summary(s, current_jti) for s in sessions]


@router.delete("/me/sessions", response_model=RevokedSessionsResponse)
@inject
async def revoke_my_sessions(
    response: Response,
    keep_current: bool = Query(
        default=False,
        description="Keep the session making this request (sign out other devices only)",
    ),
    user: User = Depends(get_current_user),
    current_jti: str = Depends(get_current_jti),
    device: DeviceInfoDTO = Depends(get_device_info),
    cookies: SessionCookies = Depends(get_cookies),
    usecase: IRevokeAllSessionsUseCase = Depends(
        Provide[Container.revoke_all_sessions_usecase]
    ),
) -> RevokedSessionsResponse:
    """Log out from all devices.

    ``keep_current=true`` spares the device making the request — the "kick
    everyone else" button. By default this signs the caller out too, so the
    auth cookies are cleared as well.
    """
    revoked = await usecase(
        user.id,
        except_jti=current_jti if keep_current else None,
        device=device,
    )
    if not keep_current:
        cookies.clear_tokens(response)
    return RevokedSessionsResponse(revoked=revoked)


@router.delete(
    "/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def revoke_my_session(
    session_id: int,
    user: User = Depends(get_current_user),
    device: DeviceInfoDTO = Depends(get_device_info),
    usecase: IRevokeUserSessionUseCase = Depends(
        Provide[Container.revoke_user_session_usecase]
    ),
) -> None:
    """Sign one device out. 404 if the session is not the caller's."""
    await usecase(user.id, SessionId(session_id), device)


@router.get("/{user_id}", response_model=PublicUserResponse)
@inject
async def read_user(
    user_id: int,
    usecase: IGetUserProfileUseCase = Depends(
        Provide[Container.get_user_profile_usecase]
    ),
) -> PublicUserResponse:
    """Public profile of one account. 404 if missing or soft-deleted.

    Deliberately unauthenticated and deliberately thin: a video page shows an
    uploader's handle to anonymous visitors, and nothing here reveals an email
    or the account's roles.
    """
    user = await usecase(UserId(user_id))
    return to_public_user_response(user)
