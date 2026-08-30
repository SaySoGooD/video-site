import hashlib
import secrets

from users_service.application.common.interfaces.security.i_one_time_token_service import (  # noqa: E501
    IOneTimeTokenService,
)
from users_service.application.common.interfaces.security.tokens import (
    GeneratedSecret,
)


class Sha256OneTimeTokenService(IOneTimeTokenService):
    """Random URL-safe secrets, stored as a plain SHA-256 digest.

    A fast hash is the right tool here, unlike for passwords: these secrets are
    256 bits of ``secrets.token_urlsafe`` entropy, so there is no dictionary to
    run and nothing for a slow KDF to buy. Hashing at all is what matters — a
    leaked database then contains no usable verification or reset links.

    No salt for the same reason, and because a salted hash could not be looked
    up by value.
    """

    def __init__(self, entropy_bytes: int = 32) -> None:
        self._entropy_bytes = entropy_bytes

    def generate(self) -> GeneratedSecret:
        plain = secrets.token_urlsafe(self._entropy_bytes)
        return GeneratedSecret(plain=plain, hashed=self.hash(plain))

    def hash(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()
