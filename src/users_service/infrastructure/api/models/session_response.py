from datetime import datetime

from pydantic import BaseModel


class SessionSummary(BaseModel):
    """One live login, as shown in "your devices".

    ``current`` marks the session the request itself is authenticated with, so
    a user does not accidentally sign out the device they are looking at.
    """

    id: int
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    current: bool = False
