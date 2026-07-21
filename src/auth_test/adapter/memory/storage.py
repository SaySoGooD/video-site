"""In-memory stand-in for the database.

A single :class:`InMemoryStorage` instance (a DI singleton) holds all rows in
plain dicts and keeps the many-to-many links in sets, exactly mirroring the
normalized schema (``user_roles``, ``role_permissions``). Full entities are
assembled on read, so callers get the same shape as the SQLAlchemy backend and
never share mutable references with the store.
"""

from dataclasses import replace

from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.session.models import AuthSession
from auth_test.entities.session.value_objects import SessionId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import UserId


class InMemoryStorage:
    def __init__(self) -> None:
        self.users: dict[UserId, User] = {}
        self.roles: dict[RoleId, Role] = {}
        self.permissions: dict[PermissionId, Permission] = {}
        self.sessions: dict[SessionId, AuthSession] = {}
        self.user_roles: set[tuple[int, int]] = set()
        self.role_permissions: set[tuple[int, int]] = set()
        self._counters = {"user": 0, "role": 0, "permission": 0, "session": 0}

    def next_id(self, kind: str) -> int:
        self._counters[kind] += 1
        return self._counters[kind]

    def build_role(self, role_id: RoleId) -> Role:
        """Return a copy of the role with its granted permissions attached."""
        role = self.roles[role_id]
        permissions = [
            self.permissions[PermissionId(pid)]
            for (rid, pid) in sorted(self.role_permissions)
            if rid == int(role_id) and PermissionId(pid) in self.permissions
        ]
        return replace(role, permissions=permissions)

    def build_user(self, user_id: UserId) -> User:
        """Return a copy of the user with its roles (and their permissions)."""
        user = self.users[user_id]
        role_ids = sorted(
            rid for (uid, rid) in self.user_roles if uid == int(user_id)
        )
        roles = [
            self.build_role(RoleId(rid))
            for rid in role_ids
            if RoleId(rid) in self.roles
        ]
        return replace(user, roles=roles)
