from enum import StrEnum
from typing import NewType

SessionId = NewType("SessionId", int)


class SessionStatus(StrEnum):
    """Derived state of a login session — never stored, always computed."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
