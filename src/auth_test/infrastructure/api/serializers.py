from auth_test.entities.user.models import User
from auth_test.infrastructure.api.models.auth import RoleSummary
from auth_test.infrastructure.api.models.user_response import UserResponse


def to_user_response(user: User) -> UserResponse:
    """Map a domain :class:`User` to its public API representation."""
    return UserResponse(
        id=int(user.id),
        email=str(user.email),
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        roles=[
            RoleSummary(id=int(r.id), name=r.name, description=r.description)
            for r in user.roles
        ],
        permissions=user.permission_codes,
    )
