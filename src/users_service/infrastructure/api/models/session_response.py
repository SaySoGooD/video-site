from datetime import datetime

from pydantic import BaseModel


class SessionSummary(BaseModel):
    """One live login, as shown in "your devices".

    ``current`` marks the session the request itself is authenticated with, so
    a user does not accidentally sign out the device they are looking at.
    """

    id: int
    status: str
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    device: str | None = None
    current: bool = False


class RevokedSessionsResponse(BaseModel):
    """How many devices a bulk sign-out actually knocked offline."""

    revoked: int


class PasswordChangedResponse(BaseModel):
    """The outcome of a password change: everyone was signed out."""

    detail: str
    sessions_revoked: int
