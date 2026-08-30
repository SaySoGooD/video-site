from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from users_service.entities.audit.value_objects import AuditAction, AuditEventId
from users_service.entities.user.value_objects import UserId


@dataclass
class AuditEvent:
    """One security-relevant thing that happened, and who it happened to.

    ``user_id`` is optional on purpose: a failed login against an address that
    does not exist still deserves a record, and that record has no user to
    point at. ``metadata`` carries the few extra details specific to an action
    (which session was revoked, why a login failed) without growing a column
    per action.

    Audit rows are append-only — nothing in the service updates or deletes
    them.
    """

    id: AuditEventId
    action: AuditAction
    created_at: datetime
    user_id: UserId | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
