from abc import ABC, abstractmethod
from datetime import datetime

from users_service.entities.session.models import AuthSession
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import UserId


class ISessionRepository(ABC):
    """Persistence port for server-side login sessions."""

    @abstractmethod
    async def add(self, session: AuthSession) -> AuthSession:
        ...

    @abstractmethod
    async def get_by_id(self, session_id: SessionId) -> AuthSession | None:
        ...

    @abstractmethod
    async def get_by_jti(self, jti: str) -> AuthSession | None:
        ...

    @abstractmethod
    async def list_active_for_user(self, user_id: UserId) -> list[AuthSession]:
        """Return the user's non-revoked, unexpired sessions, newest first."""
        ...

    @abstractmethod
    async def revoke(self, jti: str, moment: datetime) -> None:
        """Revoke a single session by its token id (idempotent)."""
        ...

    @abstractmethod
    async def revoke_all_for_user(
        self,
        user_id: UserId,
        moment: datetime,
        except_jti: str | None = None,
    ) -> int:
        """Revoke every live session of a user, optionally sparing one.

        ``except_jti`` is what makes "sign out my other devices" different
        from "sign out everywhere". Returns how many sessions were revoked.
        """
        ...
