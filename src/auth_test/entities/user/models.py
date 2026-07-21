from dataclasses import dataclass, field
from datetime import datetime

from auth_test.entities.role.models import Role
from auth_test.entities.user.value_objects import Email, UserId


@dataclass
class User:
    """A person able to authenticate and be authorized against resources.

    ``password_hash`` never holds a plaintext password — hashing happens in
    the security adapter before the entity is built. ``is_active`` drives the
    soft-delete rule: a deactivated user stays in the database but can no
    longer log in.
    """

    id: UserId
    email: Email
    password_hash: str

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None

    is_active: bool = True
    is_superuser: bool = False

    created_at: datetime | None = None
    updated_at: datetime | None = None

    roles: list[Role] = field(default_factory=list)

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
        """Flattened, de-duplicated list of ``resource:action`` codes."""
        codes = {perm.code for role in self.roles for perm in role.permissions}
        return sorted(codes)
