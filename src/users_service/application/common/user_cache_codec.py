"""Serialize a :class:`User` (with roles and permissions) to/from JSON.

Used to cache the fully-loaded user so authentication can skip the database
round trip. Lives in the application layer because it depends only on domain
entities and the standard library. Datetimes are stored as ISO-8601 strings.
"""

import json
from datetime import datetime

from users_service.entities.permission.models import Permission
from users_service.entities.permission.value_objects import PermissionId
from users_service.entities.role.models import Role
from users_service.entities.role.value_objects import RoleId
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import (
    Email,
    UserId,
    Username,
    VisitorId,
)


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
            "username": str(user.username),
            "password_hash": user.password_hash,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "email_verified_at": _iso(user.email_verified_at),
            "visitor_id": user.visitor_id,
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
    visitor_id = data["visitor_id"]
    return User(
        id=UserId(data["id"]),
        email=Email(data["email"]),
        username=Username(data["username"]),
        password_hash=data["password_hash"],
        display_name=data["display_name"],
        is_active=data["is_active"],
        is_superuser=data["is_superuser"],
        email_verified_at=_parse(data["email_verified_at"]),
        visitor_id=VisitorId(visitor_id) if visitor_id is not None else None,
        created_at=_parse(data["created_at"]),
        updated_at=_parse(data["updated_at"]),
        roles=roles,
    )
