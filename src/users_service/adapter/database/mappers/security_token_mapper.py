from users_service.adapter.database.orm_models.security_token_orm import (
    SecurityTokenORM,
)
from users_service.entities.security_token.models import SecurityToken
from users_service.entities.security_token.value_objects import (
    SecurityTokenId,
    TokenPurpose,
)
from users_service.entities.user.value_objects import UserId


def security_token_to_entity(row: SecurityTokenORM) -> SecurityToken:
    return SecurityToken(
        id=SecurityTokenId(row.id),
        user_id=UserId(row.user_id),
        purpose=TokenPurpose(row.purpose),
        token_hash=row.token_hash,
        created_at=row.created_at,
        expires_at=row.expires_at,
        used_at=row.used_at,
    )
