"""Helper for writing audit rows from inside a use case's transaction.

Kept as a function rather than a service so the event is written by the very
unit of work that performed the action: either both land or neither does, and
an audit row can never claim something the database did not do.
"""

from datetime import UTC, datetime
from typing import Any

from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.entities.audit.models import AuditEvent
from users_service.entities.audit.value_objects import AuditAction, AuditEventId
from users_service.entities.user.value_objects import UserId


async def record(
    uow: IUnitOfWork,
    action: AuditAction,
    *,
    user_id: UserId | None = None,
    device: DeviceInfoDTO | None = None,
    **metadata: Any,
) -> None:
    """Append one event to the audit log."""
    device = device or DeviceInfoDTO()
    await uow.audit_log.add(
        AuditEvent(
            id=AuditEventId(0),
            action=action,
            created_at=datetime.now(UTC),
            user_id=user_id,
            ip_address=device.ip_address,
            user_agent=device.user_agent,
            metadata=metadata,
        )
    )
