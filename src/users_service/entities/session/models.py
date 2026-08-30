from dataclasses import dataclass
from datetime import UTC, datetime

from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import UserId, VisitorId


@dataclass
class AuthSession:
    """A server-side record of one login on one device.

    Every issued token carries a ``jti`` (JWT ID) that points back to a row
    here. Because the server owns this record, logout and soft-delete can
    revoke a token immediately by flipping ``revoked`` — a stateless JWT alone
    could not be invalidated before expiry.

    The device fields exist so a user can review and kill their own sessions
    ("logged in from Firefox on Windows, 2 days ago") — they are descriptive
    only and never take part in an authorization decision.

    ``is_valid`` treats a naive ``expires_at`` as UTC, since some backends
    (e.g. SQLite) return naive datetimes.
    """

    id: SessionId
    user_id: UserId
    jti: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False

    visitor_id: VisitorId | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    last_used_at: datetime | None = None

    def is_valid(self, now: datetime | None = None) -> bool:
        """Return whether the session is still usable at ``now``."""
        moment = now or datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return not self.revoked and moment < expires_at
