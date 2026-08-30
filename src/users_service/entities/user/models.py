from dataclasses import dataclass, field
from datetime import datetime

from users_service.entities.role.models import Role
from users_service.entities.user.value_objects import (
    Email,
    UserId,
    Username,
    VisitorId,
)


@dataclass
class User:
    """An account able to authenticate and be authorized against resources.

    ``email`` is private (login identity), ``username`` is the public handle
    other visitors see. ``password_hash`` never holds a plaintext password —
    hashing happens in the security adapter before the entity is built.
    ``is_active`` drives the soft-delete rule: a deactivated user stays in the
    database but can no longer log in.

    ``email_verified_at`` is a timestamp rather than a flag: knowing *when*
    an address was confirmed is what makes an audit trail useful later.

    ``visitor_id`` is the browser this account was created from. It is kept so
    the analytics side can stitch a visitor's pre-signup activity to the
    account, and is never exposed on the public profile.
    """

    id: UserId
    email: Email
    username: Username
    password_hash: str

    display_name: str | None = None

    is_active: bool = True
    is_superuser: bool = False

    email_verified_at: datetime | None = None

    visitor_id: VisitorId | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    roles: list[Role] = field(default_factory=list)

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    def has_permission(self, resource: str, action: str) -> bool:
        """Return whether the user may perform ``action`` on ``resource``.

        Superusers bypass the role check entirely. Everyone else is granted
        access only if one of their roles carries the matching permission.
        """
        if self.is_superuser:
            return True
        return any(role.grants(resource, action) for role in self.roles)

    @property
    def permission_codes(self) -> list[str]:
        """Flattened, de-duplicated list of ``resource.action`` codes."""
        codes = {perm.code for role in self.roles for perm in role.permissions}
        return sorted(codes)

    @property
    def public_name(self) -> str:
        """What other visitors see — the display name, or the handle."""
        return self.display_name or str(self.username)
