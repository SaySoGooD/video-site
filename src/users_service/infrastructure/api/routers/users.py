"""Account endpoints that are *about* users rather than about logging in.

``/auth/*`` is the credential flow; ``/users/*`` is the profile and device
surface a video site's account page is built from. ``PATCH /users/me`` is the
same operation as ``PATCH /auth/me`` under the name the account page expects.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from users_service.application.auth.interfaces.i_update_user_usecase import (
    IUpdateUserUseCase,
)
from users_service.application.common.dto import UpdateUserDTO
from users_service.application.users.interfaces.i_get_user_profile_usecase import (
    IGetUserProfileUseCase,
)
from users_service.application.users.interfaces.i_list_user_sessions_usecase import (
    IListUserSessionsUseCase,
)
from users_service.application.users.interfaces.i_revoke_user_session_usecase import (
    IRevokeUserSessionUseCase,
)
from users_service.dependency_injection import Container
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId
from users_service.infrastructure.api.dependencies import (
    get_current_jti,
    get_current_user,
)
from users_service.infrastructure.api.models.auth import UpdateProfileRequest
from users_service.infrastructure.api.models.public_user_response import (
    PublicUserResponse,
)
from users_service.infrastructure.api.models.session_response import SessionSummary
from users_service.infrastructure.api.models.user_response import UserResponse
from users_service.infrastructure.api.serializers import (
    to_public_user_response,
    to_session_summary,
    to_user_response,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserResponse)
@inject
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    usecase: IUpdateUserUseCase = Depends(Provide[Container.update_user_usecase]),
) -> UserResponse:
    """Edit the current user's profile (alias of ``PATCH /auth/me``)."""
    updated = await usecase(
        user.id,
        UpdateUserDTO(
            username=body.username,
            display_name=body.display_name,
            email=str(body.email) if body.email is not None else None,
        ),
    )
    return to_user_response(updated)


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


@router.delete(
    "/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def revoke_my_session(
    session_id: int,
    user: User = Depends(get_current_user),
    usecase: IRevokeUserSessionUseCase = Depends(
        Provide[Container.revoke_user_session_usecase]
    ),
) -> None:
    """Sign one device out. 404 if the session is not the caller's."""
    await usecase(user.id, SessionId(session_id))


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
