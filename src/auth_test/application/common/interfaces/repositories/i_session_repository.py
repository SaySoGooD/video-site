from abc import ABC, abstractmethod

from auth_test.entities.session.models import AuthSession
from auth_test.entities.user.value_objects import UserId


class ISessionRepository(ABC):
    """Persistence port for server-side login sessions."""

    @abstractmethod
    async def add(self, session: AuthSession) -> AuthSession:
        ...

    @abstractmethod
    async def get_by_jti(self, jti: str) -> AuthSession | None:
        ...

    @abstractmethod
    async def revoke(self, jti: str) -> None:
        """Revoke a single session by its token id (idempotent)."""
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UserId) -> None:
        """Revoke every active session belonging to a user."""
        ...
