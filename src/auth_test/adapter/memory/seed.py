from datetime import UTC, datetime

from auth_test.adapter.memory.storage import InMemoryStorage
from auth_test.adapter.seed_data import (
    PERMISSIONS,
    ROLE_DESCRIPTIONS,
    ROLE_GRANTS,
    USERS,
)
from auth_test.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import Email, UserId


def seed_memory(storage: InMemoryStorage, hasher: IPasswordHasher) -> None:
    """Populate the in-memory storage with demo data unless it already exists."""
    if storage.users:
        return

    permission_ids: dict[tuple[str, str], PermissionId] = {}
    for resource, action, description in PERMISSIONS:
        permission_id = PermissionId(storage.next_id("permission"))
        storage.permissions[permission_id] = Permission(
            id=permission_id,
            resource=resource,
            action=action,
            description=description,
        )
        permission_ids[(resource, action)] = permission_id

    role_ids: dict[str, RoleId] = {}
    for name, grants in ROLE_GRANTS.items():
        role_id = RoleId(storage.next_id("role"))
        storage.roles[role_id] = Role(
            id=role_id, name=name, description=ROLE_DESCRIPTIONS[name], permissions=[]
        )
        for key in grants:
            storage.role_permissions.add((int(role_id), int(permission_ids[key])))
        role_ids[name] = role_id

    now = datetime.now(UTC)
    for email, password, first, last, is_super, role_name in USERS:
        user_id = UserId(storage.next_id("user"))
        storage.users[user_id] = User(
            id=user_id,
            email=Email(email),
            password_hash=hasher.hash(password),
            first_name=first,
            last_name=last,
            is_active=True,
            is_superuser=is_super,
            created_at=now,
            updated_at=now,
            roles=[],
        )
        storage.user_roles.add((int(user_id), int(role_ids[role_name])))
