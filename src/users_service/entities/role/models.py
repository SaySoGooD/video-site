from dataclasses import dataclass, field

from users_service.entities.permission.models import Permission
from users_service.entities.role.value_objects import RoleId


@dataclass
class Role:
    """A named bundle of permissions granted to users.

    Roles are the indirection between users and permissions: a user is
    granted roles, and each role carries a set of permissions. This keeps
    access rules manageable (RBAC).
    """

    id: RoleId
    name: str
    description: str | None = None
    permissions: list[Permission] = field(default_factory=list)

    def grants(self, resource: str, action: str) -> bool:
        """Return whether this role permits ``action`` on ``resource``."""
        return any(
            perm.resource == resource and perm.action == action
            for perm in self.permissions
        )
