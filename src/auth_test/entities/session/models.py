from dataclasses import dataclass
from datetime import UTC, datetime

from auth_test.entities.session.value_objects import SessionId
from auth_test.entities.user.value_objects import UserId


@dataclass
class AuthSession:
    """A server-side record of one login.

    Every issued access token carries a ``jti`` (JWT ID) that points back to a
    row here. Because the server owns this record, logout and soft-delete can
    revoke a token immediately by flipping ``revoked`` — a stateless JWT alone
    could not be invalidated before expiry.

    ``is_valid`` treats a naive ``expires_at`` as UTC, since some backends
    (e.g. SQLite) return naive datetimes.
    """

    id: SessionId
    user_id: UserId
    jti: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False

    def is_valid(self, now: datetime | None = None) -> bool:
        """Return whether the session is still usable at ``now``."""
        moment = now or datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return not self.revoked and moment < expires_at
