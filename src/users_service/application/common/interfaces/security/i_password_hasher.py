from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """Port for turning plaintext passwords into verifiable hashes."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Return a salted, one-way hash of ``plain_password``."""
        ...

    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Return whether ``plain_password`` matches ``password_hash``."""
        ...
