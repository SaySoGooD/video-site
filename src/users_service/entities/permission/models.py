from dataclasses import dataclass

from users_service.entities.permission.value_objects import PermissionId


@dataclass
class Permission:
    """A single access rule: the right to perform ``action`` on ``resource``.

    A permission is the atomic unit of authorization. The pair
    (``resource``, ``action``) is unique across the system, e.g.
    ("content", "moderate") or ("users", "ban").
    """

    id: PermissionId
    resource: str
    action: str
    description: str | None = None

    @property
    def code(self) -> str:
        """Human-readable identifier, e.g. ``content.read``."""
        return f"{self.resource}.{self.action}"
