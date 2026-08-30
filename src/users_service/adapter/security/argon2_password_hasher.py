from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)


class Argon2PasswordHasher(IPasswordHasher):
    """Password hashing with Argon2id (via ``argon2-cffi``).

    Argon2id is a modern, memory-hard KDF (winner of the Password Hashing
    Competition): its memory cost makes GPU/ASIC brute-forcing far more
    expensive than with PBKDF2. Salting and parameters are embedded in the
    output string (``$argon2id$v=19$m=...,t=...,p=...$<salt>$<hash>``), so no
    external salt handling is needed. Swappable for PBKDF2 behind the
    :class:`IPasswordHasher` port.
    """

    def __init__(self) -> None:
        self._hasher = _Argon2Hasher()

    def hash(self, plain_password: str) -> str:
        return self._hasher.hash(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
