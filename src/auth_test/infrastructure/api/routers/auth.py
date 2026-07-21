from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_test.application.auth.interfaces.i_delete_user_usecase import (
    IDeleteUserUseCase,
)
from auth_test.application.auth.interfaces.i_login_usecase import ILoginUseCase
from auth_test.application.auth.interfaces.i_logout_usecase import ILogoutUseCase
from auth_test.application.auth.interfaces.i_refresh_token_usecase import (
    IRefreshTokenUseCase,
)
from auth_test.application.auth.interfaces.i_register_user_usecase import (
    IRegisterUserUseCase,
)
from auth_test.application.auth.interfaces.i_update_user_usecase import (
    IUpdateUserUseCase,
)
from auth_test.application.common.dto import (
    AuthTokenDTO,
    LoginDTO,
    RegisterUserDTO,
    UpdateUserDTO,
)
from auth_test.dependency_injection import Container
from auth_test.entities.user.models import User
from auth_test.infrastructure.api.dependencies import get_current_user
from auth_test.infrastructure.api.models.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
)
from auth_test.infrastructure.api.models.user_response import UserResponse
from auth_test.infrastructure.api.serializers import to_user_response

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer_scheme = HTTPBearer(auto_error=True)


def _to_token_response(token: AuthTokenDTO) -> TokenResponse:
    return TokenResponse(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        token_type=token.token_type,
        access_expires_at=token.access_expires_at,
        refresh_expires_at=token.refresh_expires_at,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def register(
    body: RegisterRequest,
    usecase: IRegisterUserUseCase = Depends(
        Provide[Container.register_user_usecase]
    ),
) -> UserResponse:
    """Create a new account. 409 if the email is taken, 422 if passwords differ."""
    user = await usecase(
        RegisterUserDTO(
            email=str(body.email),
            password=body.password,
            password_repeat=body.password_repeat,
            first_name=body.first_name,
            last_name=body.last_name,
            middle_name=body.middle_name,
        )
    )
    return to_user_response(user)


@router.post("/login", response_model=TokenResponse)
@inject
async def login(
    body: LoginRequest,
    usecase: ILoginUseCase = Depends(Provide[Container.login_usecase]),
) -> TokenResponse:
    """Exchange email + password for an access + refresh pair. 401 on bad creds."""
    token = await usecase(LoginDTO(email=str(body.email), password=body.password))
    return _to_token_response(token)


@router.post("/refresh", response_model=TokenResponse)
@inject
async def refresh(
    body: RefreshRequest,
    usecase: IRefreshTokenUseCase = Depends(
        Provide[Container.refresh_token_usecase]
    ),
) -> TokenResponse:
    """Swap a valid refresh token for a new pair (rotates it). 401 if invalid."""
    token = await usecase(body.refresh_token)
    return _to_token_response(token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    _: User = Depends(get_current_user),
    usecase: ILogoutUseCase = Depends(Provide[Container.logout_usecase]),
) -> None:
    """Revoke the current session so the token can no longer be used."""
    await usecase(credentials.credentials)


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
            first_name=body.first_name,
            last_name=body.last_name,
            middle_name=body.middle_name,
            email=str(body.email) if body.email is not None else None,
        ),
    )
    return to_user_response(updated)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_me(
    user: User = Depends(get_current_user),
    usecase: IDeleteUserUseCase = Depends(Provide[Container.delete_user_usecase]),
) -> None:
    """Soft-delete the current account: deactivate it and revoke its sessions."""
    await usecase(user.id)
