from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from users_service.entities.user.models import User


@dataclass
class DeviceInfoDTO:
    """Where a request is coming from.

    Filled in by the API layer from the visitor cookie and request headers.
    Descriptive only: it is stored on sessions and audit events so a user can
    recognise their own devices and an investigation has something to go on,
    and the ``visitor_id`` is what lets the analytics side join browser
    activity to an account. It never influences authentication.
    """

    visitor_id: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    device: str | None = None


@dataclass
class RegisterUserDTO:
    """Input for registering a new account."""

    email: str
    username: str
    password: str
    password_repeat: str
    display_name: str | None = None
    visitor_id: str | None = None


@dataclass
class UpdateUserDTO:
    """Partial profile update; ``None`` fields are left unchanged."""

    username: str | None = None
    display_name: str | None = None
    email: str | None = None


@dataclass
class LoginDTO:
    """Credentials supplied at login."""

    email: str
    password: str


@dataclass
class ChangePasswordDTO:
    """A password change made from inside a logged-in session."""

    current_password: str
    new_password: str
    new_password_repeat: str


@dataclass
class ResetPasswordDTO:
    """A password reset being completed with a mailed token."""

    token: str
    password: str
    password_repeat: str


@dataclass
class AuthTokenDTO:
    """The token pair handed back to a client after login or refresh."""

    access_token: str
    refresh_token: str
    token_type: str
    access_expires_at: datetime
    refresh_expires_at: datetime


@dataclass
class AuthResultDTO:
    """What a successful login or refresh produces.

    The user travels alongside the tokens so the API can answer "you are now
    logged in as ..." in the same round trip — a browser using cookie auth
    never sees the tokens themselves and would otherwise need a second call.
    """

    tokens: AuthTokenDTO
    user: "User"


@dataclass
class EmailMessageDTO:
    """One transactional email, ready to hand to a sender."""

    to: str
    subject: str
    body: str


@dataclass
class RateLimitDecision:
    """The verdict on one attempt against a rate-limited key."""

    allowed: bool
    remaining: int
    retry_after_seconds: int
