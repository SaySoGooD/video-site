from dataclasses import dataclass
from datetime import UTC, datetime

from users_service.entities.session.value_objects import SessionId, SessionStatus
from users_service.entities.user.value_objects import UserId, VisitorId


@dataclass
class AuthSession:
    """A server-side record of one login on one device.

    Every issued token carries a ``jti`` (JWT ID) that points back to a row
    here. Because the server owns this record, logout and soft-delete can
    revoke a token immediately by stamping ``revoked_at`` — a stateless JWT
    alone could not be invalidated before expiry.

    Status is **derived**, never stored: a session is revoked if it has a
    ``revoked_at``, expired if its ``expires_at`` has passed, active otherwise.
    Keeping a separate status column would let the two disagree.

    The device fields exist so a user can review and kill their own sessions
    ("Firefox on Windows, last seen 2 days ago") — they are descriptive only
    and never take part in an authorization decision.
    """

    id: SessionId
    user_id: UserId
    jti: str
    created_at: datetime
    expires_at: datetime

    revoked_at: datetime | None = None

    visitor_id: VisitorId | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    device: str | None = None
    last_seen_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def status(self, now: datetime | None = None) -> SessionStatus:
        """Derive the session's state at ``now``."""
        if self.is_revoked:
            return SessionStatus.REVOKED
        if not self._not_expired(now):
            return SessionStatus.EXPIRED
        return SessionStatus.ACTIVE

    def is_valid(self, now: datetime | None = None) -> bool:
        """Return whether the session is still usable at ``now``."""
        return not self.is_revoked and self._not_expired(now)

    def _not_expired(self, now: datetime | None = None) -> bool:
        """Compare against ``expires_at``, treating a naive value as UTC.

        Some backends (e.g. SQLite) hand back naive datetimes.
        """
        moment = now or datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return moment < expires_at
