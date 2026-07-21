from auth_test.adapter.database.orm_models.session_orm import SessionORM
from auth_test.entities.session.models import AuthSession
from auth_test.entities.session.value_objects import SessionId
from auth_test.entities.user.value_objects import UserId


def session_to_entity(row: SessionORM) -> AuthSession:
    return AuthSession(
        id=SessionId(row.id),
        user_id=UserId(row.user_id),
        jti=row.jti,
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked=row.revoked,
    )
