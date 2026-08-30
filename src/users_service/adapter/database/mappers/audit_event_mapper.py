from users_service.adapter.database.orm_models.audit_event_orm import AuditEventORM
from users_service.entities.audit.models import AuditEvent
from users_service.entities.audit.value_objects import AuditAction, AuditEventId
from users_service.entities.user.value_objects import UserId


def audit_event_to_entity(row: AuditEventORM) -> AuditEvent:
    return AuditEvent(
        id=AuditEventId(row.id),
        action=AuditAction(row.action),
        created_at=row.created_at,
        user_id=UserId(row.user_id) if row.user_id is not None else None,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        metadata=dict(row.event_metadata or {}),
    )
