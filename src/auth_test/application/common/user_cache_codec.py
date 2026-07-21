"""Serialize a :class:`User` (with roles and permissions) to/from JSON.

Used to cache the fully-loaded user so authentication can skip the database
round trip. Lives in the application layer because it depends only on domain
entities and the standard library. Datetimes are stored as ISO-8601 strings.
"""

import json
from datetime import datetime

from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import Email, UserId


def user_cache_key(user_id: UserId) -> str:
    return f"auth:user:{int(user_id)}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def dumps(user: User) -> str:
    return json.dumps(
        {
            "id": int(user.id),
            "email": str(user.email),
            "password_hash": user.password_hash,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "middle_name": user.middle_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": _iso(user.created_at),
            "updated_at": _iso(user.updated_at),
            "roles": [
                {
                    "id": int(role.id),
                    "name": role.name,
                    "description": role.description,
                    "permissions": [
                        {
                            "id": int(perm.id),
                            "resource": perm.resource,
                            "action": perm.action,
                            "description": perm.description,
                        }
                        for perm in role.permissions
                    ],
                }
                for role in user.roles
            ],
        }
    )


def loads(raw: str) -> User:
    data = json.loads(raw)
    roles = [
        Role(
            id=RoleId(role["id"]),
            name=role["name"],
            description=role["description"],
            permissions=[
                Permission(
                    id=PermissionId(perm["id"]),
                    resource=perm["resource"],
                    action=perm["action"],
                    description=perm["description"],
                )
                for perm in role["permissions"]
            ],
        )
        for role in data["roles"]
    ]
    return User(
        id=UserId(data["id"]),
        email=Email(data["email"]),
        password_hash=data["password_hash"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        middle_name=data["middle_name"],
        is_active=data["is_active"],
        is_superuser=data["is_superuser"],
        created_at=_parse(data["created_at"]),
        updated_at=_parse(data["updated_at"]),
        roles=roles,
    )
