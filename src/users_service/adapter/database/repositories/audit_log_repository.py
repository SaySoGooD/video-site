from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from users_service.adapter.database.mappers.audit_event_mapper import (
    audit_event_to_entity,
)
from users_service.adapter.database.orm_models.audit_event_orm import AuditEventORM
from users_service.application.common.interfaces.repositories.i_audit_log_repository import (  # noqa: E501
    IAuditLogRepository,
)
from users_service.entities.audit.models import AuditEvent
from users_service.entities.user.value_objects import UserId


class SqlAlchemyAuditLogRepository(IAuditLogRepository):
    """Append-only: this repository deliberately has no update or delete."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AuditEvent) -> AuditEvent:
        row = AuditEventORM(
            user_id=int(event.user_id) if event.user_id is not None else None,
            action=str(event.action),
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            event_metadata=event.metadata,
            created_at=event.created_at,
        )
        self._session.add(row)
        await self._session.flush()
        return audit_event_to_entity(row)

    async def list_for_user(
        self, user_id: UserId, limit: int = 50
    ) -> list[AuditEvent]:
        result = await self._session.execute(
            select(AuditEventORM)
            .where(AuditEventORM.user_id == int(user_id))
            .order_by(AuditEventORM.id.desc())
            .limit(limit)
        )
        return [audit_event_to_entity(row) for row in result.scalars().all()]
