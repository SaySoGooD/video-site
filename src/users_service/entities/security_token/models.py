from dataclasses import dataclass
from datetime import UTC, datetime

from users_service.entities.security_token.value_objects import (
    SecurityTokenId,
    TokenPurpose,
)
from users_service.entities.user.value_objects import UserId


@dataclass
class SecurityToken:
    """A single-use, expiring secret mailed to a user.

    Only the **hash** of the secret is stored. The plaintext exists once, in
    the email; a database dump therefore does not hand an attacker the ability
    to confirm addresses or reset passwords. This mirrors how passwords are
    handled — with the difference that these tokens are high-entropy random
    values, so a fast hash is sufficient and no salt is needed.

    A token is usable exactly once: ``used_at`` is stamped when it is spent.
    """

    id: SecurityTokenId
    user_id: UserId
    purpose: TokenPurpose
    token_hash: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def is_usable(self, now: datetime | None = None) -> bool:
        """Return whether the token may still be spent at ``now``."""
        moment = now or datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return not self.is_used and moment < expires_at
