from users_service.entities.session.models import AuthSession
from users_service.entities.user.models import User
from users_service.infrastructure.api.models.public_user_response import (
    PublicUserResponse,
)
from users_service.infrastructure.api.models.role_summary import RoleSummary
from users_service.infrastructure.api.models.session_response import SessionSummary
from users_service.infrastructure.api.models.user_response import UserResponse


def to_user_response(user: User) -> UserResponse:
    """Map a domain :class:`User` to the owner's view of the account."""
    return UserResponse(
        id=int(user.id),
        email=str(user.email),
        username=str(user.username),
        display_name=user.display_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        visitor_id=user.visitor_id,
        created_at=user.created_at,
        roles=[
            RoleSummary(id=int(r.id), name=r.name, description=r.description)
            for r in user.roles
        ],
        permissions=user.permission_codes,
    )


def to_public_user_response(user: User) -> PublicUserResponse:
    """Map a domain :class:`User` to what other visitors may see."""
    return PublicUserResponse(
        id=int(user.id),
        username=str(user.username),
        display_name=user.display_name,
        created_at=user.created_at,
    )


def to_session_summary(
    session: AuthSession, current_jti: str | None = None
) -> SessionSummary:
    """Map a login session to its "your devices" row."""
    return SessionSummary(
        id=int(session.id),
        created_at=session.created_at,
        expires_at=session.expires_at,
        last_used_at=session.last_used_at,
        user_agent=session.user_agent,
        ip_address=session.ip_address,
        current=current_jti is not None and session.jti == current_jti,
    )
