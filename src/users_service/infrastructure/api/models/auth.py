from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from users_service.infrastructure.api.models.user_response import UserResponse

USERNAME_PATTERN = r"^[a-zA-Z0-9_]{3,30}$"


class RegisterRequest(BaseModel):
    """Registration payload; ``password`` and ``password_repeat`` must match."""

    email: EmailStr
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    password_repeat: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class UpdateProfileRequest(BaseModel):
    """Partial profile update; omitted fields are left unchanged."""

    username: str | None = Field(default=None, pattern=USERNAME_PATTERN)
    display_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Body of ``POST /auth/refresh``.

    A browser leaves this empty: its refresh token travels in the HttpOnly
    cookie. Non-browser clients that hold the token themselves pass it here.
    """

    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class SessionResponse(BaseModel):
    """What login and refresh return.

    ``tokens`` is ``null`` whenever cookie auth is enabled — the browser got
    them as HttpOnly cookies and must not see them in JSON. ``csrf_token`` is
    the value to echo in the ``X-CSRF-Token`` header on unsafe requests.
    """

    user: UserResponse
    csrf_token: str | None = None
    tokens: TokenResponse | None = None
