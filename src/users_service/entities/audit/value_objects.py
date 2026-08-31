from enum import StrEnum
from typing import NewType

AuditEventId = NewType("AuditEventId", int)


class AuditAction(StrEnum):
    """The security-relevant things that can happen to an account.

    A closed set rather than free text: an investigation is only as good as
    its ability to filter, and a typo'd action name is a hole in the record.
    """

    REGISTER = "REGISTER"
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    SESSION_REVOKED = "SESSION_REVOKED"
    USER_BANNED = "USER_BANNED"
    USER_UNBANNED = "USER_UNBANNED"
