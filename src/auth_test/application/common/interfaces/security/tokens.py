from dataclasses import dataclass
from datetime import datetime

from auth_test.entities.user.value_objects import UserId


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
