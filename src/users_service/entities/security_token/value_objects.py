from enum import StrEnum
from typing import NewType

SecurityTokenId = NewType("SecurityTokenId", int)


class TokenPurpose(StrEnum):
    """What a one-time token entitles its bearer to do.

    The purpose is part of the lookup, so a verification link can never be
    replayed as a password reset.
    """

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
