from users_service.adapter.database.orm_models.session_orm import SessionORM
from users_service.entities.session.models import AuthSession
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import UserId, VisitorId


def session_to_entity(row: SessionORM) -> AuthSession:
    return AuthSession(
        id=SessionId(row.id),
        user_id=UserId(row.user_id),
        jti=row.jti,
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        visitor_id=(
            VisitorId(row.visitor_id) if row.visitor_id is not None else None
        ),
        user_agent=row.user_agent,
        ip_address=row.ip_address,
        device=row.device,
        last_seen_at=row.last_seen_at,
    )
