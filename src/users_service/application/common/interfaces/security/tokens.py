from dataclasses import dataclass
from datetime import datetime

from users_service.entities.user.value_objects import UserId


@dataclass
class TokenPayload:
    """Decoded contents of a token.

    ``token_type`` distinguishes an ``access`` token (sent on every request)
    from a ``refresh`` token (used only to mint new access tokens), so one
    cannot be used in place of the other.
    """

    user_id: UserId
    jti: str
    token_type: str
    expires_at: datetime


@dataclass
class IssuedToken:
    """A freshly minted token plus the metadata needed to persist a session."""

    token: str
    jti: str
    expires_at: datetime


@dataclass
class GeneratedSecret:
    """A freshly minted one-time secret and the hash to store for it.

    ``plain`` leaves the service exactly once, in an email; only ``hashed``
    is ever persisted.
    """

    plain: str
    hashed: str
