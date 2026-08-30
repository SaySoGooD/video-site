from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Request, Response, status

from users_service.application.auth.interfaces.i_forgot_password_usecase import (
    IForgotPasswordUseCase,
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
from users_service.application.auth.interfaces.i_reset_password_usecase import (
    IResetPasswordUseCase,
)
from users_service.application.auth.interfaces.i_verify_email_usecase import (
    IVerifyEmailUseCase,
)
from users_service.application.common.dto import (
    AuthResultDTO,
    DeviceInfoDTO,
    LoginDTO,
    RegisterUserDTO,
    ResetPasswordDTO,
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
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
)
from users_service.infrastructure.api.models.message_response import MessageResponse
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
    device: DeviceInfoDTO = Depends(get_device_info),
    visitor_id: str | None = Depends(get_visitor_id),
    usecase: IRegisterUserUseCase = Depends(
        Provide[Container.register_user_usecase]
    ),
) -> UserResponse:
    """Create a new account and mail a confirmation link.

    409 if the email or username is taken, 422 if the passwords differ, 429 if
    this address has created too many accounts. Registration does not log the
    user in — the frontend calls ``/auth/login`` next — but it does record the
    browser's ``visitor_id``, which is what ties the visitor's pre-signup
    activity to the new account.
    """
    user = await usecase(
        RegisterUserDTO(
            email=str(body.email),
            username=body.username,
            password=body.password,
            password_repeat=body.password_repeat,
            display_name=body.display_name,
            visitor_id=visitor_id,
        ),
        device,
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
    """Exchange email + password for a session.

    401 on bad credentials, 429 once the attempt limit for this address or
    this account is exhausted.
    """
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
    device: DeviceInfoDTO = Depends(get_device_info),
    cookies: SessionCookies = Depends(get_cookies),
    usecase: ILogoutUseCase = Depends(Provide[Container.logout_usecase]),
) -> None:
    """Revoke the current session and clear the browser's auth cookies."""
    await usecase(token, device)
    cookies.clear_tokens(response)


@router.get("/verify-email", response_model=UserResponse)
@inject
async def verify_email(
    token: str = Query(min_length=1),
    device: DeviceInfoDTO = Depends(get_device_info),
    usecase: IVerifyEmailUseCase = Depends(Provide[Container.verify_email_usecase]),
) -> UserResponse:
    """Confirm an email address with a mailed token.

    A ``GET`` because it is opened by clicking a link. 400 if the link is
    unknown, already used or expired — the three are not distinguished.
    """
    user = await usecase(token, device)
    return to_user_response(user)


@router.post("/forgot-password", response_model=MessageResponse)
@inject
async def forgot_password(
    body: ForgotPasswordRequest,
    device: DeviceInfoDTO = Depends(get_device_info),
    usecase: IForgotPasswordUseCase = Depends(
        Provide[Container.forgot_password_usecase]
    ),
) -> MessageResponse:
    """Mail a reset link if the address has an account.

    Always answers the same way. Telling the caller whether the address exists
    would turn this endpoint into an account-enumeration oracle.
    """
    await usecase(str(body.email), device)
    return MessageResponse(
        detail="If that address has an account, a reset link is on its way."
    )


@router.post("/reset-password", response_model=MessageResponse)
@inject
async def reset_password(
    body: ResetPasswordRequest,
    device: DeviceInfoDTO = Depends(get_device_info),
    usecase: IResetPasswordUseCase = Depends(
        Provide[Container.reset_password_usecase]
    ),
) -> MessageResponse:
    """Set a new password from a mailed token and sign every device out."""
    await usecase(
        ResetPasswordDTO(
            token=body.token,
            password=body.password,
            password_repeat=body.password_repeat,
        ),
        device,
    )
    return MessageResponse(
        detail="Password updated. All sessions have been signed out."
    )


@router.get("/me", response_model=UserResponse)
async def read_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return to_user_response(user)
