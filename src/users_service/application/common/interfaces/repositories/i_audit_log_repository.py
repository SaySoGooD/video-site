from abc import ABC, abstractmethod

from users_service.entities.audit.models import AuditEvent
from users_service.entities.user.value_objects import UserId


class IAuditLogRepository(ABC):
    """Append-only persistence port for security events."""

    @abstractmethod
    async def add(self, event: AuditEvent) -> AuditEvent:
        ...

    @abstractmethod
    async def list_for_user(
        self, user_id: UserId, limit: int = 50
    ) -> list[AuditEvent]:
        """Return a user's most recent events, newest first."""
        ...
