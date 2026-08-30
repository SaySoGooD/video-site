from abc import ABC, abstractmethod

from users_service.application.common.interfaces.security.tokens import (
    GeneratedSecret,
)


class IOneTimeTokenService(ABC):
    """Port for minting and re-hashing the secrets sent in emails.

    Two operations, deliberately separate: ``generate`` produces a secret the
    caller mails out once and a hash it stores, ``hash`` re-derives that hash
    when the secret comes back, so a lookup never needs the plaintext.
    """

    @abstractmethod
    def generate(self) -> GeneratedSecret:
        """Return a fresh high-entropy secret together with its hash."""
        ...

    @abstractmethod
    def hash(self, secret: str) -> str:
        """Return the stored form of ``secret``."""
        ...
