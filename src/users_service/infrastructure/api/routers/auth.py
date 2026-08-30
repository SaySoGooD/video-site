from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request, Response, status

from users_service.application.auth.interfaces.i_delete_user_usecase import (
    IDeleteUserUseCase,
)
from users_service.application.auth.interfaces.i_login_usecase import ILoginUseCase
from users_service.application.auth.interfaces.i_logout_usecase import (
    ILogoutUseCase,
)
from users_service.application.auth.interfaces.i_refresh_token_usecase import (
    IRefreshTokenUseCase,
)
from users_service.application.auth.interfaces.i_register_user_usecase import (
    IRegisterUserUseCase,
)
from users_service.application.auth.interfaces.i_update_user_usecase import (
    IUpdateUserUseCase,
)
from users_service.application.common.dto import (
    AuthResultDTO,
    DeviceInfoDTO,
    LoginDTO,
    RegisterUserDTO,
    UpdateUserDTO,
)
from users_service.application.common.errors import AuthenticationError
from users_service.dependency_injection import Container
from users_service.entities.user.models import User
from users_service.infrastructure.api.cookies import SessionCookies
from users_service.infrastructure.api.dependencies import (
    get_access_token,
    get_config,
    get_cookies,
    get_current_user,
    get_device_info,
    get_visitor_id,
)
from users_service.infrastructure.api.models.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SessionResponse,
    TokenResponse,
    UpdateProfileRequest,
)
from users_service.infrastructure.api.models.user_response import UserResponse
from users_service.infrastructure.api.serializers import to_user_response
from users_service.infrastructure.config import Config

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_session_response(
    result: AuthResultDTO,
    response: Response,
    cookies: SessionCookies,
    config: Config,
) -> SessionResponse:
    """Hand the tokens to the client the way this deployment is configured.

    With cookie auth the tokens go into HttpOnly cookies and are deliberately
    left out of the body — a browser script must not be able to read them. A
    token-mode deployment (mobile app, another service) gets them in the JSON
    instead.
    """
    if config.COOKIE_AUTH_ENABLED:
        csrf_token = cookies.set_tokens(response, result.tokens)
        return SessionResponse(
            user=to_user_response(result.user), csrf_token=csrf_token
        )

    return SessionResponse(
        user=to_user_response(result.user),
        tokens=TokenResponse(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token,
            token_type=result.tokens.token_type,
            access_expires_at=result.tokens.access_expires_at,
            refresh_expires_at=result.tokens.refresh_expires_at,
        ),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def register(
    body: RegisterRequest,
    visitor_id: str | None = Depends(get_visitor_id),
    usecase: IRegisterUserUseCase = Depends(
        Provide[Container.register_user_usecase]
    ),
) -> UserResponse:
    """Create a new account.

    409 if the email or username is taken, 422 if the passwords differ.
    Registration does not log the user in — the frontend calls ``/auth/login``
    next — but it does record the browser's ``visitor_id``, which is what ties
    the visitor's pre-signup activity to the new account.
    """
    user = await usecase(
        RegisterUserDTO(
            email=str(body.email),
            username=body.username,
            password=body.password,
            password_repeat=body.password_repeat,
            display_name=body.display_name,
            visitor_id=visitor_id,
        )
    )
    return to_user_response(user)


@router.post("/login", response_model=SessionResponse)
@inject
async def login(
    body: LoginRequest,
    response: Response,
    device: DeviceInfoDTO = Depends(get_device_info),
    cookies: SessionCookies = Depends(get_cookies),
    config: Config = Depends(get_config),
    usecase: ILoginUseCase = Depends(Provide[Container.login_usecase]),
) -> SessionResponse:
    """Exchange email + password for a session. 401 on bad credentials."""
    result = await usecase(
        LoginDTO(email=str(body.email), password=body.password), device
    )
    return _to_session_response(result, response, cookies, config)


@router.post("/refresh", response_model=SessionResponse)
@inject
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    device: DeviceInfoDTO = Depends(get_device_info),
    cookies: SessionCookies = Depends(get_cookies),
    config: Config = Depends(get_config),
    usecase: IRefreshTokenUseCase = Depends(
        Provide[Container.refresh_token_usecase]
    ),
) -> SessionResponse:
    """Swap a valid refresh token for a new session (rotates it). 401 if invalid.

    The token comes from the HttpOnly cookie for browsers, or from the body for
    clients that hold it themselves.
    """
    refresh_token = cookies.read_refresh_token(request) or (
        body.refresh_token if body is not None else None
    )
    if not refresh_token:
        raise AuthenticationError("Missing refresh token")

    result = await usecase(refresh_token, device)
    return _to_session_response(result, response, cookies, config)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def logout(
    response: Response,
    token: str = Depends(get_access_token),
    _: User = Depends(get_current_user),
    cookies: SessionCookies = Depends(get_cookies),
    usecase: ILogoutUseCase = Depends(Provide[Container.logout_usecase]),
) -> None:
    """Revoke the current session and clear the browser's auth cookies."""
    await usecase(token)
    cookies.clear_tokens(response)


@router.get("/me", response_model=UserResponse)
async def read_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return to_user_response(user)


@router.patch("/me", response_model=UserResponse)
@inject
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    usecase: IUpdateUserUseCase = Depends(Provide[Container.update_user_usecase]),
) -> UserResponse:
    """Edit the current user's profile fields."""
    updated = await usecase(
        user.id,
        UpdateUserDTO(
            username=body.username,
            display_name=body.display_name,
            email=str(body.email) if body.email is not None else None,
        ),
    )
    return to_user_response(updated)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_me(
    response: Response,
    user: User = Depends(get_current_user),
    cookies: SessionCookies = Depends(get_cookies),
    usecase: IDeleteUserUseCase = Depends(Provide[Container.delete_user_usecase]),
) -> None:
    """Soft-delete the current account: deactivate it and revoke its sessions."""
    await usecase(user.id)
    cookies.clear_tokens(response)
