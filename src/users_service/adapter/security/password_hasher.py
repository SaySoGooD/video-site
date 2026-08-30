import hashlib
import hmac
import os

from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)


class PBKDF2PasswordHasher(IPasswordHasher):
    """Salted, slow one-way password hashing using PBKDF2-HMAC-SHA256.

    Passwords are never stored in plaintext. Each password gets its own random
    salt, so identical passwords produce different hashes and precomputed
    ("rainbow table") attacks do not apply. Verification is constant-time to
    avoid leaking information through timing.

    Stored format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.
    """

    _ALGORITHM = "pbkdf2_sha256"

    def __init__(self, iterations: int = 390_000, salt_bytes: int = 16) -> None:
        self._iterations = iterations
        self._salt_bytes = salt_bytes

    def hash(self, plain_password: str) -> str:
        salt = os.urandom(self._salt_bytes)
        digest = self._derive(plain_password, salt, self._iterations)
        return f"{self._ALGORITHM}${self._iterations}${salt.hex()}${digest.hex()}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations, salt_hex, digest_hex = password_hash.split("$")
        except ValueError:
            return False

        if algorithm != self._ALGORITHM:
            return False

        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = self._derive(plain_password, salt, int(iterations))
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _derive(password: str, salt: bytes, iterations: int) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
