from dataclasses import dataclass
from datetime import datetime


@dataclass
class RegisterUserDTO:
    """Input for registering a new account."""

    email: str
    password: str
    password_repeat: str
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None


@dataclass
class UpdateUserDTO:
    """Partial profile update; ``None`` fields are left unchanged."""

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    email: str | None = None


@dataclass
class LoginDTO:
    """Credentials supplied at login."""

    email: str
    password: str


@dataclass
class AuthTokenDTO:
    """The token pair handed back to a client after login or refresh."""

    access_token: str
    refresh_token: str
    token_type: str
    access_expires_at: datetime
    refresh_expires_at: datetime
