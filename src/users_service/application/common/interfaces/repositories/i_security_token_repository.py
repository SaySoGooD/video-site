from abc import ABC, abstractmethod

from users_service.entities.security_token.models import SecurityToken
from users_service.entities.security_token.value_objects import TokenPurpose
from users_service.entities.user.value_objects import UserId


class ISecurityTokenRepository(ABC):
    """Persistence port for one-time email verification / reset tokens."""

    @abstractmethod
    async def add(self, token: SecurityToken) -> SecurityToken:
        ...

    @abstractmethod
    async def get_by_hash(
        self, token_hash: str, purpose: TokenPurpose
    ) -> SecurityToken | None:
        """Look a token up by its hash *and* purpose.

        The purpose is part of the key so a link issued for one flow cannot be
        spent in another.
        """
        ...

    @abstractmethod
    async def mark_used(self, token: SecurityToken) -> None:
        """Spend the token so it cannot be replayed (idempotent)."""
        ...

    @abstractmethod
    async def invalidate_for_user(
        self, user_id: UserId, purpose: TokenPurpose
    ) -> None:
        """Spend every outstanding token of one purpose for a user.

        Issuing a new link invalidates the previous ones, and a completed
        password reset invalidates any other reset link already in flight.
        """
        ...
